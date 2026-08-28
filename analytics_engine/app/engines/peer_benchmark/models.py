"""Peer benchmark data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class EntityMetricSnapshot(BaseModel):
    """Extracted supervisory metrics for an entity."""
    entity_id: uuid.UUID
    sector: str
    size_tier: str
    mtti_minutes: float = 0.0
    escalation_rate: float = 0.0
    stale_case_ratio: float = 0.0
    coverage_gap_ratio: float = 0.0
    execution_gap_rate: float = 0.0
    total_alerts: int = 0
    total_cases: int = 0
    total_crown_jewels: int = 0


class PeerBenchmarkDraft(BaseModel):
    """Evaluated cohort benchmark ready for database persistence."""
    benchmark_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    sector: str
    size_tier: str
    metric_name: str
    period_start: datetime
    period_end: datetime
    peer_group_size: int
    mean_val: float
    std_dev: float
    p25: float
    p50: float
    p75: float
    p90: float
    is_low_confidence: bool = False
    fallback_level: str = "EXACT_COHORT"  # EXACT_COHORT, SECTOR_FALLBACK, GLOBAL_FALLBACK, BASELINE_FALLBACK


class EntityPeerEvaluation(BaseModel):
    """Evaluation result for an entity against its peer cohort."""
    entity_id: uuid.UUID
    sector: str
    size_tier: str
    period_start: datetime
    period_end: datetime
    peer_group_size: int
    is_low_confidence: bool
    fallback_applied: str
    dampening_factor: float = 1.0
    metric_z_scores: Dict[str, float] = Field(default_factory=dict)
    metric_percentiles: Dict[str, float] = Field(default_factory=dict)
    mean_risk_z_score: float = 0.0
    peer_deviation_score: float = 50.0
