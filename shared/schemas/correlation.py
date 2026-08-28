"""Correlation schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class CorrelationBase(BaseModel):
    """Base fields for correlation link."""
    correlation_type: str = Field(..., description="REPEAT_ASSET_ALERT, TFIDF_NOTE_SIMILARITY, JACCARD_INCIDENT")
    primary_event_id: uuid.UUID
    correlated_event_id: uuid.UUID
    asset_id: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    shared_attributes: Dict[str, Any] = Field(default_factory=dict)
    rationale: str


class CorrelationCreate(CorrelationBase):
    """Payload to create correlation record."""
    entity_id: uuid.UUID


class CorrelationOut(CorrelationBase):
    """Response DTO for correlation link."""
    model_config = ConfigDict(from_attributes=True)

    correlation_id: uuid.UUID
    entity_id: uuid.UUID
    created_at: datetime
