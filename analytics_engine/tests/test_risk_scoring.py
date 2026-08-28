"""Unit tests for Weighted Risk Scoring Engine and Normalization Formulas."""

from datetime import datetime, timezone
import uuid
import pytest

from analytics_engine.engines.execution_gap.models import ExecutionGapFindingDraft
from analytics_engine.engines.negative_space.models import NegativeSpaceFindingDraft
from analytics_engine.engines.risk_scoring.engine import RiskScoringEngine
from analytics_engine.engines.risk_scoring.formulas import (
    compute_composite_risk_score,
    compute_execution_gap_subscore,
    compute_negative_space_subscore,
    determine_trend_direction,
    map_score_to_risk_tier,
)


def test_subscore_formulas(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies sub-score mathematical normalization and bounding in [0, 100]."""
    # 2 execution gap findings (severity 80, confidence 0.90)
    eg_findings = [
        ExecutionGapFindingDraft(
            entity_id=entity_id,
            rule_id="EG-01",
            rule_name="Uninvestigated Alerts",
            rule_category="TRIAGE",
            severity="HIGH",
            severity_score=80,
            confidence=0.90,
            period_start=sample_now,
            period_end=sample_now,
            description="test",
            rationale="test",
            evidence_record_ids=["e1"],
        ),
        ExecutionGapFindingDraft(
            entity_id=entity_id,
            rule_id="EG-02",
            rule_name="Missing Escalation",
            rule_category="ESCALATION",
            severity="HIGH",
            severity_score=80,
            confidence=0.90,
            period_start=sample_now,
            period_end=sample_now,
            description="test",
            rationale="test",
            evidence_record_ids=["e2"],
        ),
    ]

    s_eg = compute_execution_gap_subscore(eg_findings, alert_count=50)
    assert 0.0 <= s_eg <= 100.0

    # 1 negative space finding
    ns_findings = [
        NegativeSpaceFindingDraft(
            entity_id=entity_id,
            check_id="NS-01",
            check_name="Cliff",
            check_category="LOG_SILENCE",
            severity="HIGH",
            severity_score=85,
            confidence=0.90,
            period_start=sample_now,
            period_end=sample_now,
            expected_volume=100.0,
            observed_volume=10.0,
            drop_percentage=90.0,
            rationale="test",
            is_degraded=False,
            degradation_factor=1.0,
        )
    ]
    s_ns = compute_negative_space_subscore(ns_findings)
    assert 0.0 <= s_ns <= 100.0


def test_composite_risk_score_calculation():
    """Verifies 45/35/20 composite weighting."""
    # S_EG = 80, S_NS = 60, S_Peer = 40
    # Composite = 0.45 * 80 + 0.35 * 60 + 0.20 * 40 = 36 + 21 + 8 = 65.0
    comp = compute_composite_risk_score(s_eg=80.0, s_ns=60.0, s_peer=40.0)
    assert comp == 65.0


def test_risk_tier_and_trend_mapping():
    """Verifies tier thresholds and trend direction."""
    assert map_score_to_risk_tier(15.0) == "LOW"
    assert map_score_to_risk_tier(35.0) == "GUARDED"
    assert map_score_to_risk_tier(65.0) == "ELEVATED"
    assert map_score_to_risk_tier(88.0) == "CRITICAL"

    # Trends
    assert determine_trend_direction(current_score=70.0, previous_score=60.0) == "DETERIORATING"
    assert determine_trend_direction(current_score=50.0, previous_score=60.0) == "IMPROVING"
    assert determine_trend_direction(current_score=61.0, previous_score=60.0) == "STABLE"


def test_risk_scoring_engine_full_run(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies complete run of RiskScoringEngine."""
    engine = RiskScoringEngine()

    draft = engine.calculate_score(
        entity_id=entity_id,
        period_start=sample_now,
        period_end=sample_now,
        execution_gap_findings=[],
        negative_space_findings=[],
        peer_deviation_score=50.0,
        alert_count=100,
        previous_score=15.0,
    )

    # 0.45 * 0 + 0.35 * 0 + 0.20 * 50 = 10.0
    assert draft.composite_risk_score == 10.0
    assert draft.risk_tier == "LOW"
    assert draft.trend_direction == "IMPROVING"
    assert "Composite Risk Score: 10.0/100" in draft.rationale_summary
