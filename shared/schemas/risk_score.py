"""Risk score schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import RiskTier, TrendDirection


class RiskBreakdown(BaseModel):
    """Component risk scores and weights."""
    execution_gap_score: float = Field(..., ge=0.0, le=100.0, description="45% weight component")
    negative_space_score: float = Field(..., ge=0.0, le=100.0, description="35% weight component")
    peer_deviation_score: float = Field(..., ge=0.0, le=100.0, description="20% weight component")
    weights_applied: Dict[str, float] = Field(
        default_factory=lambda: {
            "execution_gap": 0.45,
            "negative_space": 0.35,
            "peer_deviation": 0.20,
        }
    )


class RiskScoreCalculateRequest(BaseModel):
    """Request payload to trigger risk score computation."""
    entity_id: uuid.UUID
    period_start: datetime
    period_end: datetime


class RiskScoreOut(BaseModel):
    """Response DTO for composite risk score."""
    model_config = ConfigDict(from_attributes=True)

    score_id: uuid.UUID
    entity_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    composite_risk_score: float
    execution_gap_score: float
    negative_space_score: float
    peer_deviation_score: float
    weights_applied: Dict[str, Any]
    risk_tier: str
    trend_direction: str
    rationale_summary: str
    calculated_at: datetime
