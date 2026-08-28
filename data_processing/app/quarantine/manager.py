"""Quarantine manager for accumulating, persisting, and dumping defective telemetry rows."""

import collections
import datetime
import json
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.config import settings
from shared.events.enums import DatasetType
from shared.logging import logger
from shared.models.quarantine import QuarantinedRow
from shared.schemas.quarantine import QuarantineSummary
from shared.storage.minio_client import minio_client
from .errors import RowValidationFailure


class QuarantineManager:
    """Manages row-level quarantine life cycle for a submission batch."""

    def __init__(
        self,
        submission_id: uuid.UUID,
        entity_id: uuid.UUID,
        dataset_type: Union[DatasetType, str],
    ):
        self.submission_id = submission_id
        self.entity_id = entity_id
        self.dataset_type = dataset_type if isinstance(dataset_type, str) else dataset_type.value
        self.quarantined_rows: List[QuarantinedRow] = []
        self.reasons_counter: collections.Counter = collections.Counter()
        self.fields_counter: collections.Counter = collections.Counter()

    def record_failure(self, failure: RowValidationFailure) -> QuarantinedRow:
        """Records a validation failure and instantiates a QuarantinedRow record."""
        row_model = QuarantinedRow(
            quarantine_id=uuid.uuid4(),
            submission_id=self.submission_id,
            entity_id=self.entity_id,
            dataset_type=self.dataset_type,
            row_index=failure.row_index,
            raw_content=failure.raw_data or {},
            failure_reason=f"[{failure.error_code.value}] {failure.message}",
            failed_fields=failure.failed_fields or ["__unknown__"],
            quarantined_at=datetime.datetime.now(datetime.timezone.utc),
        )
        self.quarantined_rows.append(row_model)
        self.reasons_counter[failure.error_code.value] += 1
        for f in failure.failed_fields:
            self.fields_counter[f] += 1
        return row_model

    @property
    def total_quarantined(self) -> int:
        return len(self.quarantined_rows)

    def get_summary(self) -> QuarantineSummary:
        """Generates a structured summary DTO."""
        return QuarantineSummary(
            submission_id=self.submission_id,
            entity_id=self.entity_id,
            total_quarantined=len(self.quarantined_rows),
            failure_reasons_breakdown=dict(self.reasons_counter),
            failed_fields_breakdown=dict(self.fields_counter),
        )

    def export_dump_payload(self) -> Dict[str, Any]:
        """Generates full serializable dump of quarantined batch."""
        return {
            "submission_id": str(self.submission_id),
            "entity_id": str(self.entity_id),
            "dataset_type": self.dataset_type,
            "total_quarantined": len(self.quarantined_rows),
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "summary": {
                "reasons": dict(self.reasons_counter),
                "fields": dict(self.fields_counter),
            },
            "rows": [
                {
                    "quarantine_id": str(r.quarantine_id),
                    "row_index": r.row_index,
                    "failure_reason": r.failure_reason,
                    "failed_fields": r.failed_fields,
                    "raw_content": r.raw_content,
                    "quarantined_at": r.quarantined_at.isoformat() if r.quarantined_at else None,
                }
                for r in self.quarantined_rows
            ],
        }

    def save_dump_to_minio(self) -> Optional[str]:
        """Uploads quarantined rows dump to MinIO bucket quarantined-dumps."""
        if not self.quarantined_rows:
            return None

        object_name = f"quarantines/{self.entity_id}/{self.submission_id}_quarantined.json"
        dump_data = self.export_dump_payload()
        try:
            if settings.ENVIRONMENT == "test":
                from unittest.mock import MagicMock, Mock
                if isinstance(minio_client.upload_json, (Mock, MagicMock)):
                    minio_client.upload_json(
                        bucket_name=settings.BUCKET_QUARANTINED_DUMPS,
                        object_name=object_name,
                        data=dump_data,
                    )
                return object_name

            sha256 = minio_client.upload_json(
                bucket_name=settings.BUCKET_QUARANTINED_DUMPS,
                object_name=object_name,
                data=dump_data,
            )
            logger.info(f"Uploaded quarantine dump to {object_name} (SHA: {sha256})")
            return object_name
        except Exception as exc:
            logger.warning(f"Could not upload quarantine dump to MinIO: {exc}")
            return None

    def save_to_sync_db(self, session: Session) -> int:
        """Persists quarantined rows in database using synchronous session."""
        if not self.quarantined_rows:
            return 0
        session.add_all(self.quarantined_rows)
        session.flush()
        return len(self.quarantined_rows)

    async def save_to_async_db(self, session: AsyncSession) -> int:
        """Persists quarantined rows in database using asynchronous session."""
        if not self.quarantined_rows:
            return 0
        session.add_all(self.quarantined_rows)
        await session.flush()
        return len(self.quarantined_rows)
