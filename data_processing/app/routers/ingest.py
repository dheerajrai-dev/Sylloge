"""Ingestion API endpoint."""

import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from shared.events.enums import DatasetType
from shared.schemas.submission import IngestRequest, IngestResult
from ..pipeline.ingestion_service import IngestionPipelineService

router = APIRouter(prefix="/api/v1/process", tags=["Ingestion"])


class IngestPayload(BaseModel):
    """Flexible payload for triggering ingestion pipeline."""
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    file_path: Optional[str] = None
    raw_content: Optional[str] = None
    format_hint: Optional[str] = None


@router.post("/ingest", response_model=IngestResult, status_code=status.HTTP_200_OK)
async def trigger_ingest(
    payload: IngestPayload,
    db: AsyncSession = Depends(get_db),
) -> IngestResult:
    """Triggers end-to-end parsing, row validation, quarantine, and normalization for a submission batch."""
    try:
        result = await IngestionPipelineService.process_async(
            db=db,
            submission_id=payload.submission_id,
            entity_id=payload.entity_id,
            dataset_type=payload.dataset_type,
            file_path=payload.file_path,
            raw_content=payload.raw_content,
            format_hint=payload.format_hint,
        )
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion processing failed: {str(exc)}",
        )
