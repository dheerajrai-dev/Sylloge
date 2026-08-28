"""Peer benchmark schemas."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PeerBenchmarkBase(BaseModel):
    """Base peer benchmark metrics."""
    sector: str
    size_tier: str
    metric_name: str
    period_start: datetime
    period_end: datetime
    peer_group_size: int = Field(..., ge=0)
    mean_val: float
    std_dev: float
    p25: float
    p50: float
    p75: float
    p90: float
    is_low_confidence: bool = False


class PeerBenchmarkCreate(PeerBenchmarkBase):
    """Payload to create benchmark record."""
    pass


class PeerBenchmarkOut(PeerBenchmarkBase):
    """Response DTO for benchmark record."""
    model_config = ConfigDict(from_attributes=True)

    benchmark_id: uuid.UUID
    calculated_at: datetime


class BenchmarkCohortSummary(BaseModel):
    """Summary of cohort metrics for comparison."""
    sector: str
    size_tier: str
    period_start: datetime
    period_end: datetime
    peer_group_size: int
    metrics: List[PeerBenchmarkOut]
