"""Quarantine schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType


class QuarantinedRowOut(BaseModel):
    """Response DTO for quarantined defective row."""
    model_config = ConfigDict(from_attributes=True)

    quarantine_id: uuid.UUID
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    row_index: int
    raw_content: Dict[str, Any]
    failure_reason: str
    failed_fields: List[str]
    quarantined_at: datetime


class QuarantineSummary(BaseModel):
    """Summary of quarantined records for an entity or submission."""
    submission_id: Optional[uuid.UUID] = None
    entity_id: uuid.UUID
    total_quarantined: int
    failure_reasons_breakdown: Dict[str, int]
    failed_fields_breakdown: Dict[str, int]
