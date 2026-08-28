"""API Request and Response schemas for analytics engine."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field

from shared.schemas.benchmark import PeerBenchmarkOut
from shared.schemas.correlation import CorrelationOut
from shared.schemas.finding import ExecutionGapFindingOut, NegativeSpaceFindingOut
from shared.schemas.risk_score import RiskScoreOut
from ..engines.execution_gap.models import RuleDefinition
from ..engines.explainability.models import RationaleCardData
from ..engines.negative_space.models import CheckDefinition


class AnalyzeRequest(BaseModel):
    """Payload to trigger comprehensive analytics pipeline execution."""
    entity_id: uuid.UUID
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    sector: Optional[str] = None
    size_tier: Optional[str] = None
    events: Optional[List[Dict[str, Any]]] = None
    persist_to_db: bool = True
    previous_score: Optional[float] = None


class AnalyzeResponse(BaseModel):
    """Consolidated analytics results across all 6 engines."""
    entity_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    execution_gap_count: int
    negative_space_count: int
    correlations_count: int
    burst_clusters_count: int
    peer_group_size: int
    is_low_confidence_peer: bool
    risk_score: RiskScoreOut
    execution_gap_findings: List[ExecutionGapFindingOut]
    negative_space_findings: List[NegativeSpaceFindingOut]
    correlations: List[CorrelationOut]
    benchmarks: List[PeerBenchmarkOut]
    rationale_cards: List[RationaleCardData]


class RuleListResponse(BaseModel):
    """Response containing active execution gap and negative space rules."""
    execution_gap_rules: List[RuleDefinition]
    negative_space_checks: List[CheckDefinition]
