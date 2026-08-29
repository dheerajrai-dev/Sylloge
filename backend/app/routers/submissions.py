"""Data Submissions, Ingestion Upload, and Live Polling API Router."""

from datetime import datetime, timezone
import io
import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_supervisor
from shared.config import settings
from shared.db.session import get_db
from shared.logging import logger
from shared.models.entity import Entity
from shared.models.quarantine import QuarantinedRow
from shared.events.enums import DatasetType, SubmissionStatus
from shared.models.submission import RawSubmission
from shared.schemas.auth import TokenPayload
from shared.schemas.quarantine import QuarantinedRowOut
from shared.schemas.submission import IngestResult, SubmissionOut
from shared.storage.merkle import sha256_hash_bytes
from shared.storage.minio_client import minio_client
from ..services.clients import DataProcessingClient

router = APIRouter(prefix="/api/v1", tags=["Submissions & Ingestion"])


class IngestionJobStatus(BaseModel):
    job_id: str
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: str
    status: str  # PENDING, INGESTING, VALIDATING, NORMALIZING, COMPLETED, FAILED
    progress_pct: int
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    errors: List[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime] = None


@router.post("/submissions/upload", response_model=IngestResult, status_code=status.HTTP_202_ACCEPTED)
@router.post("/ingestion/upload", response_model=IngestResult, status_code=status.HTTP_202_ACCEPTED)
async def upload_submission(
    file: UploadFile = File(...),
    entity_id: uuid.UUID = Form(...),
    dataset_type: str = Form(...),
    profile_id: Optional[uuid.UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Uploads telemetry dataset (CSV/JSON), parses, quarantines defective rows, and normalizes."""
    # 1. Verify entity exists
    ent_res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = ent_res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    file_bytes = await file.read()
    file_size = len(file_bytes)
    sha256 = sha256_hash_bytes(file_bytes)
    now = datetime.now(timezone.utc)
    submission_id = uuid.uuid4()

    # 2. Upload to MinIO
    year = now.strftime("%Y")
    month = now.strftime("%m")
    object_name = f"{entity_id}/{dataset_type}/{year}/{month}/{submission_id}_{file.filename}"

    try:
        minio_client.upload_bytes(
            bucket_name=settings.BUCKET_RAW_SUBMISSIONS,
            object_name=object_name,
            data=file_bytes,
            content_type=file.content_type or "text/csv",
        )
    except Exception as exc:
        logger.warning(f"MinIO raw upload skipped or failed: {exc}")

    # 3. Create initial RawSubmission in DB
    submission = RawSubmission(
        submission_id=submission_id,
        entity_id=entity_id,
        dataset_type=dataset_type,
        file_name=file.filename or f"{dataset_type}.csv",
        file_size_bytes=file_size,
        mime_type=file.content_type or "text/csv",
        minio_raw_path=object_name,
        sha256_hash=sha256,
        row_count=0,
        valid_row_count=0,
        quarantined_row_count=0,
        ingestion_status="VALIDATING",
        uploaded_at=now,
    )
    db.add(submission)
    await db.commit()

    # 4. Invoke Ingestion Pipeline Service
    try:
        from data_processing.app.pipeline.ingestion_service import IngestionPipelineService
        result = await IngestionPipelineService.process_async(
            db=db,
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_type,
            raw_content=file_bytes,
        )
        return result
    except Exception as exc:
        logger.warning(f"Ingestion pipeline failed: {exc}")
        return IngestResult(
            submission_id=submission_id,
            entity_id=entity_id,
            dataset_type=dataset_type,
            status=SubmissionStatus.FAILED if hasattr(SubmissionStatus, "FAILED") else "FAILED",
            total_rows=0,
            valid_rows=0,
            quarantined_rows=0,
            sha256_hash=sha256,
            error_message=str(exc),
        )


@router.get("/submissions", response_model=List[SubmissionOut])
async def list_submissions(
    entity_id: Optional[uuid.UUID] = Query(None),
    dataset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Lists raw telemetry submissions."""
    stmt = select(RawSubmission)
    if entity_id:
        stmt = stmt.where(RawSubmission.entity_id == entity_id)
    if dataset_type:
        stmt = stmt.where(RawSubmission.dataset_type == dataset_type)
    if status:
        stmt = stmt.where(RawSubmission.ingestion_status == status.upper())

    stmt = stmt.order_by(desc(RawSubmission.uploaded_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
async def get_submission(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves single submission metadata."""
    res = await db.execute(
        select(RawSubmission).where(RawSubmission.submission_id == submission_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return sub


@router.get("/submissions/{submission_id}/quarantine", response_model=List[QuarantinedRowOut])
async def get_submission_quarantined_rows(
    submission_id: uuid.UUID,
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves defective quarantined rows for a submission."""
    stmt = (
        select(QuarantinedRow)
        .where(QuarantinedRow.submission_id == submission_id)
        .order_by(QuarantinedRow.row_index)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/ingestion/jobs/recent")
async def get_recent_ingestion_jobs(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves recent submission activity feed for dashboard."""
    stmt = select(RawSubmission).order_by(desc(RawSubmission.uploaded_at)).limit(limit)
    res = await db.execute(stmt)
    submissions = list(res.scalars().all())

    return [
        {
            "job_id": str(s.submission_id),
            "submission_id": str(s.submission_id),
            "entity_id": str(s.entity_id),
            "dataset_type": s.dataset_type,
            "file_name": s.file_name,
            "status": s.ingestion_status,
            "total_rows": s.row_count,
            "valid_rows": s.valid_row_count,
            "quarantined_rows": s.quarantined_row_count,
            "uploaded_at": s.uploaded_at.isoformat(),
        }
        for s in submissions
    ]


@router.get("/ingestion/jobs/{job_id}/status", response_model=IngestionJobStatus)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Live polling endpoint for ingestion job status."""
    res = await db.execute(
        select(RawSubmission).where(RawSubmission.submission_id == job_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    status_str = sub.ingestion_status
    progress = 100 if status_str in ("NORMALIZED", "PARTIAL_SUCCESS", "FAILED") else 50

    return IngestionJobStatus(
        job_id=str(sub.submission_id),
        submission_id=sub.submission_id,
        entity_id=sub.entity_id,
        dataset_type=sub.dataset_type,
        status=status_str,
        progress_pct=progress,
        total_rows=sub.row_count,
        valid_rows=sub.valid_row_count,
        quarantined_rows=sub.quarantined_row_count,
        errors=[{"error": sub.error_summary}] if sub.error_summary else [],
        started_at=sub.uploaded_at,
        completed_at=sub.processed_at,
    )
