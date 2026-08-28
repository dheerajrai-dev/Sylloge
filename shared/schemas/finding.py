"""Finding and Explainability schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import FindingStatus, SeverityTier


class RationaleCard(BaseModel):
    """Explainability rationale card attached to findings."""
    title: str
    category: str
    severity: SeverityTier
    rationale_text: str
    evidence_record_ids: List[str]
    raw_evidence_refs: List[Any] = Field(default_factory=list)
    metric_values: Dict[str, Any] = Field(default_factory=dict)
    recommended_action: Optional[str] = None


class ExecutionGapFindingOut(BaseModel):
    """Response DTO for execution gap findings."""
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    entity_id: uuid.UUID
    rule_id: str
    rule_name: str
    rule_category: str
    severity: str
    period_start: datetime
    period_end: datetime
    status: str
    description: str
    rationale: str
    evidence_record_ids: List[str]
    raw_evidence_refs: List[Any]
    metric_values: Dict[str, Any]
    created_at: datetime


class NegativeSpaceFindingOut(BaseModel):
    """Response DTO for negative space absence findings."""
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    entity_id: uuid.UUID
    check_id: str
    check_name: str
    check_category: str
    severity: str
    period_start: datetime
    period_end: datetime
    expected_volume: float
    observed_volume: float
    drop_percentage: float
    entropy_score: Optional[float] = None
    rationale: str
    evidence_record_ids: List[str]
    created_at: datetime


class FindingFilterParams(BaseModel):
    """Query filter parameters for supervisory findings."""
    entity_id: Optional[uuid.UUID] = None
    engine: Optional[str] = None  # "execution_gap" or "negative_space"
    severity: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
