"""Correlation Engine data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class CorrelationDraft(BaseModel):
    """Evaluated correlation draft ready for database persistence."""
    correlation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    correlation_type: str  # REPEAT_ASSET_ALERT, TFIDF_NOTE_SIMILARITY, NOTE_TEMPLATE_CLONE
    primary_event_id: uuid.UUID
    correlated_event_id: uuid.UUID
    asset_id: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    shared_attributes: Dict[str, Any] = Field(default_factory=dict)
    rationale: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None))


class BurstCluster(BaseModel):
    """Clustered repeat alerts on the same asset within a sliding time window."""
    cluster_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    asset_id: str
    alert_count: int
    high_critical_count: int
    distinct_rules: List[str]
    time_window_start: datetime
    time_window_end: datetime
    evidence_record_ids: List[str]
