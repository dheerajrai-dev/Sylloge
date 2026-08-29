"""Negative space check data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class CheckDefinition(BaseModel):
    """Negative space absence check definition."""
    check_id: str
    name: str
    category: str = "LOG_SILENCE"
    severity_base: int = 80
    confidence: float = 0.90
    min_sample_size: int = 15
    description_template: str
    rationale_template: str
    recommendation: Optional[str] = None
    is_active: bool = True
    custom_params: Dict[str, Any] = Field(default_factory=dict)


class NegativeSpaceFindingDraft(BaseModel):
    """Evaluated negative space finding draft ready for persistence."""
    finding_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    check_id: str
    check_name: str
    check_category: str
    severity: str
    severity_score: int
    confidence: float
    period_start: datetime
    period_end: datetime
    expected_volume: float
    observed_volume: float
    drop_percentage: float
    entropy_score: Optional[float] = None
    rationale: str
    evidence_record_ids: List[str] = Field(default_factory=list)
    raw_evidence_refs: List[Any] = Field(default_factory=list)
    metric_values: Dict[str, Any] = Field(default_factory=dict)
    is_degraded: bool = False
    degradation_factor: float = 1.0
    recommendation: Optional[str] = None
