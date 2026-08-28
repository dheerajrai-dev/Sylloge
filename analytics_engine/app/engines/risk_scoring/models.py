"""Risk scoring data models."""

from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


class RiskScoreDraft(BaseModel):
    """Evaluated composite risk score draft ready for persistence."""
    score_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    entity_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    composite_risk_score: float = Field(..., ge=0.0, le=100.0)
    execution_gap_score: float = Field(..., ge=0.0, le=100.0)
    negative_space_score: float = Field(..., ge=0.0, le=100.0)
    peer_deviation_score: float = Field(..., ge=0.0, le=100.0)
    weights_applied: Dict[str, float] = Field(
        default_factory=lambda: {
            "execution_gap": 0.45,
            "negative_space": 0.35,
            "peer_deviation": 0.20,
        }
    )
    risk_tier: str  # LOW, GUARDED, ELEVATED, CRITICAL
    trend_direction: str  # IMPROVING, STABLE, DETERIORATING
    rationale_summary: str
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None))
