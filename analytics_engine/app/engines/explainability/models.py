"""Explainability Engine data models and Rationale Card schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class RationaleCardData(BaseModel):
    """Detailed explainability card schema adhering to Engine Spec."""
    card_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    finding_id: uuid.UUID
    entity_id: uuid.UUID
    engine_name: str  # EXECUTION_GAP, NEGATIVE_SPACE, CORRELATION, PEER_BENCHMARK
    rule_code: str
    title: str
    severity: str
    severity_score: int
    confidence: float
    summary_narrative: str
    technical_details: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[str] = None
    evidence_record_ids: List[str] = Field(default_factory=list)
    raw_evidence_refs: List[Any] = Field(default_factory=list)
    raw_row_indices: List[int] = Field(default_factory=list)
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None))
