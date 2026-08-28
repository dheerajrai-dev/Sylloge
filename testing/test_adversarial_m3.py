"""Milestone 3 Adversarial, Stress, and Boundary Attack Tests for Analytics & Scoring Core."""

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List
import uuid
import pytest

from analytics_engine import (
    AnalyticsPipeline,
    CorrelationEngine,
    ExecutionGapEngine,
    ExecutionGapRuleRegistry,
    LogicInterpreter,
    NegativeSpaceEngine,
    PeerBenchmarkEngine,
    RiskScoringEngine,
)
from analytics_engine.engines.execution_gap.models import (
    ConditionOperator,
    LogicalOperator,
    RuleCondition,
    RuleDefinition,
)
from analytics_engine.engines.negative_space.stats import (
    compute_ewma_baseline,
    compute_inter_arrival_cv,
    compute_shannon_entropy,
)
from analytics_engine.engines.peer_benchmark.stats import (
    compute_cohort_distribution,
    compute_z_score,
)
from analytics_engine.engines.risk_scoring.formulas import (
    compute_composite_risk_score,
    compute_execution_gap_subscore,
    compute_negative_space_subscore,
)
from analytics_engine.schemas.requests import AnalyzeRequest


def test_adversarial_empty_datasets_and_null_records():
    """Verifies all engines handle empty lists and null records without crashing."""
    entity_id = uuid.uuid4()
    p_start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

    eg = ExecutionGapEngine()
    ns = NegativeSpaceEngine()
    corr = CorrelationEngine()
    peer = PeerBenchmarkEngine()
    risk = RiskScoringEngine()

    # 1. Empty events
    assert eg.run([], entity_id, p_start, p_end) == []
    assert ns.run([], entity_id, p_start, p_end) == []
    assert corr.run([], entity_id, p_start, p_end) == ([], [])

    eval_res, benchmarks = peer.evaluate_entity(
        target_entity_id=entity_id,
        sector="Banking",
        size_tier="Tier-1",
        target_events=[],
    )
    assert 0.0 <= eval_res.peer_deviation_score <= 100.0
    assert eval_res.is_low_confidence is True
    assert len(benchmarks) == 5

    # 2. None / Malformed record items
    malformed_events = [None, {}, {"invalid_key": 123}, {"event_timestamp": "not_a_date"}]
    findings_eg = eg.run(malformed_events, entity_id, p_start, p_end)
    assert isinstance(findings_eg, list)


def test_adversarial_mathematical_bounds_and_zero_division():
    """Verifies mathematical invariance: all scores strictly within [0.0, 100.0] under extreme loads."""
    # 1. Zero division in Z-score when std_dev == 0
    z = compute_z_score(value=100.0, mean=100.0, std_dev=0.0)
    assert not math.isnan(z)
    assert not math.isinf(z)
    assert z == 0.0

    # 2. Single item cohort distribution
    mu, sigma, p25, p50, p75, p90 = compute_cohort_distribution([42.0])
    assert mu == 42.0
    assert sigma >= 1e-4

    # 3. Massive finding counts (1,000 critical findings)
    mock_findings = [{"severity_score": 100, "confidence": 1.0} for _ in range(1000)]
    s_eg = compute_execution_gap_subscore(mock_findings, alert_count=10)
    assert s_eg == 100.0  # Clamped at 100.0

    s_ns = compute_negative_space_subscore(mock_findings)
    assert s_ns == 100.0  # Clamped at 100.0

    # 4. Extreme composite scores
    comp_max = compute_composite_risk_score(s_eg=150.0, s_ns=200.0, s_peer=1000.0)
    assert comp_max == 100.0

    comp_min = compute_composite_risk_score(s_eg=-50.0, s_ns=-100.0, s_peer=-20.0)
    assert comp_min == 0.0


def test_adversarial_malformed_ast_conditions():
    """Verifies declarative interpreter gracefully handles corrupt AST operator trees."""
    from pydantic import ValidationError

    record = {"severity": "CRITICAL", "count": 10}

    # Corrupt operator rejected by Pydantic validation
    with pytest.raises(ValidationError):
        RuleCondition(field="severity", operator="INVALID_OP", value="CRITICAL")

    # Corrupt field path evaluates gracefully to False
    cond_corrupt_field = RuleCondition(field=".....invalid.nested..", operator=ConditionOperator.EQ, value=1)
    assert LogicInterpreter.evaluate_condition(cond_corrupt_field, record) is False

    # Regex with invalid pattern syntax (e.g. unclosed parenthesis)
    cond_bad_regex = RuleCondition(field="severity", operator=ConditionOperator.REGEX_MATCH, value="([unclosed_group")
    assert LogicInterpreter.evaluate_condition(cond_bad_regex, record) is False


def test_adversarial_unicode_and_gibberish_note_similarity():
    """Verifies TF-IDF and Jaccard do not fail on unicode, emojis, or foreign scripts."""
    corr_engine = CorrelationEngine()
    entity_id = uuid.uuid4()
    p_start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2026, 8, 2, 0, 0, 0, tzinfo=timezone.utc)

    unicode_events = [
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "investigation_records",
            "standard_event_type": "INVESTIGATION",
            "case_id": "CASE-UNICODE-1",
            "investigation_notes": "🔒 🚨 Анализ безопасности завершен. Подозрительная активность заблокирована.",
        },
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "investigation_records",
            "standard_event_type": "INVESTIGATION",
            "case_id": "CASE-UNICODE-2",
            "investigation_notes": "🔒 🚨 Анализ безопасности завершен. Подозрительная активность заблокирована.",
        },
    ]

    corrs, clusters = corr_engine.run(unicode_events, entity_id, p_start, p_end)
    assert isinstance(corrs, list)
    assert isinstance(clusters, list)


def test_adversarial_synthetic_cv_and_zero_timestamps():
    """Verifies CV computation with identical timestamps."""
    identical_times = [datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)] * 25
    cv, mu_d, sigma_d, n = compute_inter_arrival_cv(identical_times)
    assert cv == 0.0
    assert mu_d == 0.0


def test_adversarial_pipeline_single_entity_fallback():
    """Verifies full pipeline operates when only a single entity exists in platform."""
    pipeline = AnalyticsPipeline()
    entity_id = uuid.uuid4()
    p_start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2026, 8, 2, 0, 0, 0, tzinfo=timezone.utc)

    req = AnalyzeRequest(
        entity_id=entity_id,
        period_start=p_start,
        period_end=p_end,
        sector="RareDefenseSector",
        size_tier="Tier-3",
        events=[],
        persist_to_db=False,
    )

    resp = pipeline.execute_sync(request=req)
    assert resp.is_low_confidence_peer is True
    assert resp.risk_score.risk_tier == "LOW"
    assert round(resp.risk_score.composite_risk_score, 2) == 7.75
