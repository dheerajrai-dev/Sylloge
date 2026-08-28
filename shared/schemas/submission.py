"""Submission and Ingestion schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType, SubmissionStatus


class SubmissionBase(BaseModel):
    """Base fields for raw submission."""
    dataset_type: DatasetType
    file_name: str
    file_size_bytes: int
    mime_type: str


class SubmissionCreate(SubmissionBase):
    """Payload to create raw submission record."""
    entity_id: uuid.UUID
    minio_raw_path: str
    sha256_hash: str


class SubmissionOut(SubmissionBase):
    """Response DTO for raw submission."""
    model_config = ConfigDict(from_attributes=True)

    submission_id: uuid.UUID
    entity_id: uuid.UUID
    minio_raw_path: str
    sha256_hash: str
    row_count: int
    valid_row_count: int
    quarantined_row_count: int
    ingestion_status: SubmissionStatus
    error_summary: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class IngestRequest(BaseModel):
    """Worker dispatch payload for ingestion and normalization."""
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    file_path: str  # MinIO object path or local temp path


class IngestResult(BaseModel):
    """Result returned by data-processing ingestion pipeline."""
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    status: SubmissionStatus
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    sha256_hash: str
    error_message: Optional[str] = None
