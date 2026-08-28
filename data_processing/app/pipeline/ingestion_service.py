"""Ingestion Pipeline Service orchestrating parsing, row validation, quarantine, normalization, and persistence."""

import datetime
import hashlib
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.config import settings
from shared.events.enums import DatasetType, SubmissionStatus
from shared.logging import logger
from shared.models.mapping import FieldMappingProfile
from shared.models.submission import RawSubmission
from shared.schemas.submission import IngestResult
from shared.storage.merkle import sha256_hash_bytes
from shared.storage.minio_client import minio_client

from ..mapping.normalizer import CanonicalNormalizer
from ..parsers import get_parser_for_dataset
from ..quarantine.manager import QuarantineManager
from ..quarantine.validator import RowValidator


class IngestionPipelineService:
    """End-to-end ingestion and normalization pipeline executor."""

    @classmethod
    async def process_async(
        cls,
        db: AsyncSession,
        submission_id: uuid.UUID,
        entity_id: uuid.UUID,
        dataset_type: Union[DatasetType, str],
        file_path: Optional[str] = None,
        raw_content: Optional[Union[str, bytes]] = None,
        format_hint: Optional[str] = None,
    ) -> IngestResult:
        """Executes ingestion workflow asynchronously with database session."""
        dataset_enum = DatasetType(dataset_type) if isinstance(dataset_type, str) else dataset_type

        # 1. Acquire raw bytes
        content_bytes, file_sha256 = await cls._load_content_bytes_async(file_path, raw_content)

        # 2. Look up active FieldMappingProfile
        mapping_profile = await cls._get_mapping_profile_async(db, entity_id, dataset_enum)

        # 3. Execute parsing and validation pipeline
        total_rows, valid_rows, quarantined_rows, normalizer, quarantine_mgr = cls._run_pipeline(
            content_bytes=content_bytes,
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_enum,
            mapping_profile=mapping_profile,
            format_hint=format_hint,
        )

        # 4. Save entities to database
        if quarantine_mgr.total_quarantined > 0:
            await quarantine_mgr.save_to_async_db(db)

        if normalizer.total_normalized > 0:
            await normalizer.save_to_async_db(db)

        # 5. Determine lifecycle status
        if total_rows == 0:
            status = SubmissionStatus.FAILED
            err_msg = "No rows found in input data"
        elif quarantined_rows == 0:
            status = SubmissionStatus.NORMALIZED
            err_msg = None
        elif valid_rows > 0:
            status = SubmissionStatus.PARTIAL_SUCCESS
            err_msg = f"{quarantined_rows} rows quarantined due to validation errors"
        else:
            status = SubmissionStatus.FAILED
            err_msg = "All rows failed schema validation and were quarantined"

        # 6. Update RawSubmission record if it exists
        stmt = (
            update(RawSubmission)
            .where(RawSubmission.submission_id == submission_id)
            .values(
                row_count=total_rows,
                valid_row_count=valid_rows,
                quarantined_row_count=quarantined_rows,
                ingestion_status=status.value,
                error_summary=err_msg,
                processed_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        await db.execute(stmt)
        await db.commit()

        # 7. Upload quarantine dump to MinIO if errors occurred
        if quarantined_rows > 0:
            try:
                quarantine_mgr.save_dump_to_minio()
            except Exception as exc:
                logger.warning(f"Could not upload quarantine dump to MinIO: {exc}")

        return IngestResult(
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_enum,
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            quarantined_rows=quarantined_rows,
            sha256_hash=file_sha256,
            error_message=err_msg,
        )

    @classmethod
    def process_sync(
        cls,
        db: Session,
        submission_id: uuid.UUID,
        entity_id: uuid.UUID,
        dataset_type: Union[DatasetType, str],
        file_path: Optional[str] = None,
        raw_content: Optional[Union[str, bytes]] = None,
        format_hint: Optional[str] = None,
    ) -> IngestResult:
        """Executes ingestion workflow synchronously."""
        dataset_enum = DatasetType(dataset_type) if isinstance(dataset_type, str) else dataset_type

        # 1. Acquire raw bytes
        content_bytes, file_sha256 = cls._load_content_bytes_sync(file_path, raw_content)

        # 2. Look up active FieldMappingProfile
        mapping_profile = cls._get_mapping_profile_sync(db, entity_id, dataset_enum)

        # 3. Execute parsing and validation pipeline
        total_rows, valid_rows, quarantined_rows, normalizer, quarantine_mgr = cls._run_pipeline(
            content_bytes=content_bytes,
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_enum,
            mapping_profile=mapping_profile,
            format_hint=format_hint,
        )

        # 4. Save entities to database
        if quarantine_mgr.total_quarantined > 0:
            quarantine_mgr.save_to_sync_db(db)

        if normalizer.total_normalized > 0:
            normalizer.save_to_sync_db(db)

        # 5. Determine lifecycle status
        if total_rows == 0:
            status = SubmissionStatus.FAILED
            err_msg = "No rows found in input data"
        elif quarantined_rows == 0:
            status = SubmissionStatus.NORMALIZED
            err_msg = None
        elif valid_rows > 0:
            status = SubmissionStatus.PARTIAL_SUCCESS
            err_msg = f"{quarantined_rows} rows quarantined due to validation errors"
        else:
            status = SubmissionStatus.FAILED
            err_msg = "All rows failed schema validation and were quarantined"

        # 6. Update RawSubmission record if it exists
        sub = db.get(RawSubmission, submission_id)
        if sub is not None:
            sub.row_count = total_rows
            sub.valid_row_count = valid_rows
            sub.quarantined_row_count = quarantined_rows
            sub.ingestion_status = status.value
            sub.error_summary = err_msg
            sub.processed_at = datetime.datetime.now(datetime.timezone.utc)
            db.flush()

        db.commit()

        # 7. Upload quarantine dump to MinIO if errors occurred
        if quarantined_rows > 0:
            try:
                quarantine_mgr.save_dump_to_minio()
            except Exception as exc:
                logger.warning(f"Could not upload quarantine dump to MinIO: {exc}")

        return IngestResult(
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_enum,
            status=status,
            total_rows=total_rows,
            valid_rows=valid_rows,
            quarantined_rows=quarantined_rows,
            sha256_hash=file_sha256,
            error_message=err_msg,
        )

    @classmethod
    def _run_pipeline(
        cls,
        content_bytes: bytes,
        submission_id: uuid.UUID,
        entity_id: uuid.UUID,
        dataset_type: DatasetType,
        mapping_profile: Optional[FieldMappingProfile],
        format_hint: Optional[str] = None,
    ) -> Tuple[int, int, int, CanonicalNormalizer, QuarantineManager]:
        """Internal synchronous generator iteration over dataset stream."""
        parser = get_parser_for_dataset(dataset_type)
        validator = RowValidator(dataset_type, mapping_profile)
        quarantine_mgr = QuarantineManager(submission_id, entity_id, dataset_type)
        normalizer = CanonicalNormalizer(submission_id, entity_id, dataset_type, mapping_profile)

        total_rows = 0
        valid_rows = 0
        quarantined_rows = 0

        for parsed_row in parser.parse_stream(content_bytes):
            total_rows += 1
            failure = validator.validate_parsed_row(parsed_row)
            if failure is not None:
                quarantine_mgr.record_failure(failure)
                quarantined_rows += 1
            else:
                normalizer.normalize_row(parsed_row.data, parsed_row.row_index)
                valid_rows += 1

        return total_rows, valid_rows, quarantined_rows, normalizer, quarantine_mgr

    @classmethod
    async def _load_content_bytes_async(
        cls, file_path: Optional[str], raw_content: Optional[Union[str, bytes]]
    ) -> Tuple[bytes, str]:
        """Loads file content asynchronously or from memory."""
        return cls._load_content_bytes_sync(file_path, raw_content)

    @classmethod
    def _load_content_bytes_sync(
        cls, file_path: Optional[str], raw_content: Optional[Union[str, bytes]]
    ) -> Tuple[bytes, str]:
        """Loads content bytes from raw_content, local file, or MinIO."""
        if raw_content is not None:
            if isinstance(raw_content, str):
                raw_bytes = raw_content.encode("utf-8")
            else:
                raw_bytes = raw_content
            return raw_bytes, sha256_hash_bytes(raw_bytes)

        if file_path:
            # 1. Local filesystem path check
            if os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    raw_bytes = f.read()
                return raw_bytes, sha256_hash_bytes(raw_bytes)

            # 2. MinIO S3 path check
            try:
                raw_bytes = minio_client.download_bytes(
                    bucket_name=settings.BUCKET_RAW_SUBMISSIONS,
                    object_name=file_path,
                )
                return raw_bytes, sha256_hash_bytes(raw_bytes)
            except Exception as exc:
                raise FileNotFoundError(f"Could not load submission file from {file_path}: {exc}") from exc

        raise ValueError("Neither file_path nor raw_content was provided for ingestion")

    @classmethod
    async def _get_mapping_profile_async(
        cls, db: AsyncSession, entity_id: uuid.UUID, dataset_type: DatasetType
    ) -> Optional[FieldMappingProfile]:
        """Queries database for active FieldMappingProfile asynchronously."""
        stmt = (
            select(FieldMappingProfile)
            .where(
                FieldMappingProfile.entity_id == entity_id,
                FieldMappingProfile.dataset_type == dataset_type.value,
                FieldMappingProfile.is_active == True,
            )
            .order_by(FieldMappingProfile.version.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    def _get_mapping_profile_sync(
        cls, db: Session, entity_id: uuid.UUID, dataset_type: DatasetType
    ) -> Optional[FieldMappingProfile]:
        """Queries database for active FieldMappingProfile synchronously."""
        stmt = (
            select(FieldMappingProfile)
            .where(
                FieldMappingProfile.entity_id == entity_id,
                FieldMappingProfile.dataset_type == dataset_type.value,
                FieldMappingProfile.is_active == True,
            )
            .order_by(FieldMappingProfile.version.desc())
            .limit(1)
        )
        return db.scalars(stmt).first()
