"""Weighted Risk Scoring Engine implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from shared.logging import logger
from .formulas import (
    compute_composite_risk_score,
    compute_execution_gap_subscore,
    compute_negative_space_subscore,
    determine_trend_direction,
    map_score_to_risk_tier,
)
from .models import RiskScoreDraft


class RiskScoringEngine:
    """Combines Execution Gap, Negative Space, and Peer Deviation into a 0-100 score."""

    def __init__(
        self,
        weight_eg: float = 0.45,
        weight_ns: float = 0.35,
        weight_peer: float = 0.20,
    ):
        self.weight_eg = weight_eg
        self.weight_ns = weight_ns
        self.weight_peer = weight_peer

    def calculate_score(
        self,
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        execution_gap_findings: List[Any],
        negative_space_findings: List[Any],
        peer_deviation_score: float = 50.0,
        alert_count: int = 0,
        previous_score: Optional[float] = None,
    ) -> RiskScoreDraft:
        """Computes composite score and generates summary narrative."""
        # 1. Compute sub-scores
        s_eg = compute_execution_gap_subscore(execution_gap_findings, alert_count=alert_count)
        s_ns = compute_negative_space_subscore(negative_space_findings)
        s_peer = min(100.0, max(0.0, float(peer_deviation_score)))

        # 2. Composite score
        composite = compute_composite_risk_score(
            s_eg=s_eg,
            s_ns=s_ns,
            s_peer=s_peer,
            w_eg=self.weight_eg,
            w_ns=self.weight_ns,
            w_peer=self.weight_peer,
        )

        # 3. Tier & Trend
        tier = map_score_to_risk_tier(composite)
        trend = determine_trend_direction(composite, previous_score)

        # 4. Generate Rationale Narrative
        narrative_parts = []
        narrative_parts.append(
            f"Composite Risk Score: {composite}/100 ({tier} Tier). "
            f"Component breakdown: Execution Gap = {s_eg} (weight 45%), "
            f"Negative Space = {s_ns} (weight 35%), Peer Deviation = {s_peer} (weight 20%)."
        )

        top_drivers = []
        if s_eg >= 50.0:
            top_drivers.append(f"{len(execution_gap_findings)} execution gaps detected")
        if s_ns >= 50.0:
            top_drivers.append(f"{len(negative_space_findings)} negative space absence anomalies detected")
        if s_peer >= 60.0:
            top_drivers.append("statistically significant negative deviation from sector peer cohort")

        if top_drivers:
            narrative_parts.append(f" Primary risk drivers: {', '.join(top_drivers)}.")
        else:
            narrative_parts.append(" Risk indicators remain within nominal supervisory tolerances.")

        rationale_summary = "".join(narrative_parts)

        draft = RiskScoreDraft(
            entity_id=entity_id,
            period_start=period_start,
            period_end=period_end,
            composite_risk_score=composite,
            execution_gap_score=s_eg,
            negative_space_score=s_ns,
            peer_deviation_score=s_peer,
            weights_applied={
                "execution_gap": self.weight_eg,
                "negative_space": self.weight_ns,
                "peer_deviation": self.weight_peer,
            },
            risk_tier=tier,
            trend_direction=trend,
            rationale_summary=rationale_summary,
        )

        logger.info(
            f"Risk Score computed for entity {entity_id}: composite={composite}, "
            f"tier={tier}, trend={trend}"
        )
        return draft
