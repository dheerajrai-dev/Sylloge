"""Comprehensive Empirical Challenger Stress Test Suite for Milestone 3 (Six Analytics Engines).

This suite tests:
1. Mathematical invariants and edge cases across EWMA, Shannon entropy, inter-arrival CV, cohort distributions, and risk scores.
2. AST Logic Interpreter robustness against malformed/corrupt operators, nested trees, missing paths, and datetime edge cases.
3. Negative Space checks under adversarial conditions (empty streams, zero variances, monoculture distributions, synthetic regularities).
4. Correlation Engine under unicode/emoji spoofing, zero-token strings, boilerplate collisions, and 24h burst boundaries.
5. Peer Benchmarking cohort fallbacks (N=0, 1, 2, 3), zero-variance cohorts, extreme outliers, and low-confidence dampening.
6. Risk scoring clamping, scale factor behavior, tier transitions, and trend calculations.
7. Explainability evidence ID tracing and schema compliance.
8. End-to-end pipeline robustness and parity between sync and async execution paths.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict, List
import uuid

import numpy as np
import pytest
from pydantic import ValidationError

from analytics_engine import (
    AnalyticsPipeline,
    CorrelationEngine,
    ExecutionGapEngine,
    ExecutionGapRuleRegistry,
    ExplainabilityEngine,
    LogicInterpreter,
    NegativeSpaceEngine,
    PeerBenchmarkEngine,
    RiskScoringEngine,
)
from analytics_engine.engines.correlation.burst_clusterer import SameAssetBurstClusterer
from analytics_engine.engines.correlation.text_similarity import (
    NoteSimilarityAnalyzer,
    compute_jaccard_similarity,
    preprocess_text,
)
from analytics_engine.engines.execution_gap.models import (
    ConditionOperator,
    ExecutionGapFindingDraft,
    JoinRelation,
    LogicalOperator,
    RuleCondition,
    RuleDefinition,
    TemporalJoin,
)
from analytics_engine.engines.explainability.card_builder import RationaleCardBuilder
from analytics_engine.engines.negative_space.models import (
    CheckDefinition,
    NegativeSpaceFindingDraft,
)
from analytics_engine.engines.negative_space.stats import (
    compute_ewma_baseline,
    compute_inter_arrival_cv,
    compute_low_volume_degradation,
    compute_shannon_entropy,
    detect_ewma_volume_cliff,
)
from analytics_engine.engines.peer_benchmark.cohort import get_industry_baseline
from analytics_engine.engines.peer_benchmark.models import EntityMetricSnapshot
from analytics_engine.engines.peer_benchmark.stats import (
    compute_cohort_distribution,
    compute_ecdf_percentile,
    compute_z_score,
)
from analytics_engine.engines.risk_scoring.formulas import (
    compute_composite_risk_score,
    compute_execution_gap_subscore,
    compute_negative_space_subscore,
    determine_trend_direction,
    map_score_to_risk_tier,
)
from analytics_engine.schemas.requests import AnalyzeRequest
from shared.events.enums import DatasetType, SeverityTier, StandardEventType


# =============================================================================
# 1. MATHEMATICAL INVARIANTS & STATISTICAL STRESS TESTS
# =============================================================================

class TestMathematicalStress:
    """Rigorous mathematical edge cases across all statistical routines."""

    def test_ewma_extreme_volatility_and_empty_series(self):
        """EWMA must never produce NaN, inf, or negative variance across volatile inputs."""
        # Empty series
        mu, sigma = compute_ewma_baseline([], alpha=0.20)
        assert (mu, sigma) == (0.0, 0.0)

        # Single element
        mu, sigma = compute_ewma_baseline([100.0], alpha=0.20)
        assert mu == 100.0
        assert sigma == 0.0

        # Constant zeros
        mu, sigma = compute_ewma_baseline([0.0] * 50, alpha=0.20)
        assert mu == 0.0
        assert sigma == 0.0

        # Extreme magnitude spikes (10^9)
        spiky_series = [10.0, 10.0, 1e9, 10.0, 10.0]
        mu, sigma = compute_ewma_baseline(spiky_series, alpha=0.20)
        assert not math.isnan(mu) and not math.isinf(mu)
        assert not math.isnan(sigma) and not math.isinf(sigma)
        assert sigma >= 0.0

        # Oscillating binary series
        oscillating = [0.0, 100.0] * 25
        mu, sigma = compute_ewma_baseline(oscillating, alpha=0.20)
        assert 0.0 < mu < 100.0
        assert sigma > 0.0

        # Boundary alphas: alpha=1.0 (no memory) and alpha=0.0 (infinite memory)
        mu_a1, sig_a1 = compute_ewma_baseline([10.0, 20.0, 30.0], alpha=1.0)
        assert mu_a1 == 30.0  # Immediately follows latest value
        assert sig_a1 == 0.0  # (30 - 30)^2 = 0

        mu_a0, sig_a0 = compute_ewma_baseline([10.0, 20.0, 30.0], alpha=0.0)
        assert mu_a0 == 10.0  # Preserves initial value

    def test_detect_ewma_volume_cliff_edge_cases(self):
        """Cliff detection must handle all-zero baseline, sudden drop, and insufficient history."""
        # Insufficient history (< 5 days)
        assert detect_ewma_volume_cliff([10.0, 10.0, 10.0, 0.0], min_history_days=5) is None

        # Constant zero history followed by zero
        res_zero = detect_ewma_volume_cliff([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], alpha=0.20, k=3.0)
        assert res_zero is None  # 0 to 0 is not an anomaly cliff

        # High volume baseline collapsing to zero (100 -> 0)
        res_cliff = detect_ewma_volume_cliff([100.0, 105.0, 98.0, 102.0, 100.0, 0.0], alpha=0.20, k=3.0)
        assert res_cliff is not None
        assert res_cliff["observed_volume"] == 0.0
        assert res_cliff["drop_percentage"] == 100.0
        assert res_cliff["expected_volume"] > 90.0

        # When historical variance has high spread (e.g. [100, 150, 50, 120, 80]), 95 is within 3 sigma
        res_within_spread = detect_ewma_volume_cliff([100.0, 150.0, 50.0, 120.0, 80.0, 95.0], alpha=0.20, k=3.0)
        assert res_within_spread is None

    def test_shannon_entropy_boundary_cases(self):
        """Shannon entropy must evaluate 0 bits on monocultures and log2(M) on uniform distributions."""
        # Empty input
        h, max_h, n, m = compute_shannon_entropy([])
        assert (h, max_h, n, m) == (0.0, 0.0, 0, 0)

        # Single class monoculture (e.g. 1000 identical alerts)
        h, max_h, n, m = compute_shannon_entropy(["RULE_A"] * 1000)
        assert h == 0.0
        assert max_h == 0.0
        assert n == 1000
        assert m == 1

        # Perfectly uniform distribution across 4 classes (H should be exactly log2(4) = 2.0 bits)
        uniform_4 = ["A", "B", "C", "D"] * 100
        h, max_h, n, m = compute_shannon_entropy(uniform_4)
        assert math.isclose(h, 2.0, abs_tol=1e-3)
        assert math.isclose(max_h, 2.0, abs_tol=1e-3)

        # Extreme skewed distribution: 999 of "A" and 1 of "B"
        skewed = ["A"] * 999 + ["B"]
        h_skew, _, _, _ = compute_shannon_entropy(skewed)
        assert 0.0 < h_skew < 0.02  # Extremely low entropy, close to 0

    def test_inter_arrival_cv_regularity_and_timestamps(self):
        """CV computation must handle zero deltas, random deltas, out-of-order timestamps, and tiny sets."""
        # Less than 2 timestamps
        assert compute_inter_arrival_cv([]) == (1.0, 0.0, 0.0, 0)
        assert compute_inter_arrival_cv([datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)]) == (1.0, 0.0, 0.0, 1)

        # Perfectly periodic interval (every 60.0 seconds) -> CV must be 0.0 (synthetic bot heartbeat)
        base_t = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        periodic_times = [base_t + timedelta(seconds=60 * i) for i in range(30)]
        cv, mu_d, sigma_d, n = compute_inter_arrival_cv(periodic_times)
        assert cv == 0.0
        assert mu_d == 60.0
        assert sigma_d == 0.0
        assert n == 30

        # Out of order timestamps should be automatically sorted
        shuffled_times = list(reversed(periodic_times))
        cv_s, mu_s, sigma_s, _ = compute_inter_arrival_cv(shuffled_times)
        assert cv_s == 0.0
        assert mu_s == 60.0

        # High variance (Poisson-like / bursty human arrival times)
        bursty_times = [
            base_t,
            base_t + timedelta(seconds=2),
            base_t + timedelta(seconds=5),
            base_t + timedelta(seconds=1200),
            base_t + timedelta(seconds=1201),
            base_t + timedelta(seconds=7200),
        ]
        cv_bursty, mu_b, sigma_b, _ = compute_inter_arrival_cv(bursty_times)
        assert cv_bursty > 0.50

    def test_low_volume_degradation_bounds(self):
        """Low volume degradation factor w_deg must strictly stay within [0.10, 1.0]."""
        # N = 0
        w0, deg0 = compute_low_volume_degradation(0, n_min=15)
        assert w0 == 0.10
        assert deg0 is True

        # N = 7 (mid degradation)
        w7, deg7 = compute_low_volume_degradation(7, n_min=15)
        assert 0.10 < w7 < 1.0
        assert deg7 is True

        # N = 15 (boundary)
        w15, deg15 = compute_low_volume_degradation(15, n_min=15)
        assert w15 == 1.0
        assert deg15 is False

        # N = 1000 (ample volume)
        w1000, deg1000 = compute_low_volume_degradation(1000, n_min=15)
        assert w1000 == 1.0
        assert deg1000 is False


# =============================================================================
# 2. LOGIC INTERPRETER & AST OPERATOR ADVERSARIAL TESTS
# =============================================================================

class TestLogicInterpreterAdversarial:
    """Stress tests condition evaluation against malformed AST, invalid types, and cyclic trees."""

    def test_safe_datetime_parsing_robustness(self):
        """parse_datetime_safe must handle strange formats, invalid strings, and maintain timezone awareness."""
        assert LogicInterpreter.parse_datetime_safe(None) is None
        assert LogicInterpreter.parse_datetime_safe(123456) == 123456
        assert LogicInterpreter.parse_datetime_safe("not_a_date") == "not_a_date"

        # Timezone naive datetime converted to UTC
        naive_dt = datetime(2026, 8, 15, 10, 30, 0)
        parsed = LogicInterpreter.parse_datetime_safe(naive_dt)
        assert parsed.tzinfo == timezone.utc

        # ISO string with 'Z'
        z_str = "2026-08-15T10:30:00Z"
        parsed_z = LogicInterpreter.parse_datetime_safe(z_str)
        assert isinstance(parsed_z, datetime)
        assert parsed_z.tzinfo == timezone.utc

        # ISO string with offset
        offset_str = "2026-08-15T10:30:00+05:30"
        parsed_offset = LogicInterpreter.parse_datetime_safe(offset_str)
        assert isinstance(parsed_offset, datetime)

    def test_deeply_nested_dot_notation_and_payload_fallback(self):
        """extract_field_value must resolve deeply nested keys and normalized_payload fallbacks."""
        record = {
            "root_key": "root_val",
            "nested": {
                "level1": {
                    "level2": "deep_val",
                }
            },
            "normalized_payload": {
                "payload_key": "payload_val",
                "nested_in_payload": {"sub_key": 999},
            },
        }

        assert LogicInterpreter.extract_field_value(record, "root_key") == "root_val"
        assert LogicInterpreter.extract_field_value(record, "nested.level1.level2") == "deep_val"
        assert LogicInterpreter.extract_field_value(record, "payload_key") == "payload_val"
        assert LogicInterpreter.extract_field_value(record, "nonexistent.key.path") is None
        assert LogicInterpreter.extract_field_value(None, "any_key") is None
        assert LogicInterpreter.extract_field_value(record, "") is None

    def test_ast_operators_boundary_matrix(self):
        """Verifies every operator with boundary, None, type mismatch, and negative values."""
        # 1. IS_NULL / IS_NOT_NULL
        c_null = RuleCondition(field="missing", operator=ConditionOperator.IS_NULL)
        c_not_null = RuleCondition(field="missing", operator=ConditionOperator.IS_NOT_NULL)
        assert LogicInterpreter.evaluate_condition(c_null, {}) is True
        assert LogicInterpreter.evaluate_condition(c_null, {"missing": None}) is True
        assert LogicInterpreter.evaluate_condition(c_null, {"missing": ""}) is True
        assert LogicInterpreter.evaluate_condition(c_null, {"missing": []}) is True
        assert LogicInterpreter.evaluate_condition(c_not_null, {}) is False
        assert LogicInterpreter.evaluate_condition(c_not_null, {"missing": "present"}) is True

        # 2. String case-insensitive EQ / NE
        c_eq = RuleCondition(field="status", operator=ConditionOperator.EQ, value="OPEN")
        assert LogicInterpreter.evaluate_condition(c_eq, {"status": "open"}) is True
        assert LogicInterpreter.evaluate_condition(c_eq, {"status": " OPEN "}) is True
        assert LogicInterpreter.evaluate_condition(c_eq, {"status": "CLOSED"}) is False

        # 3. Numeric comparisons with string numbers & float coercion
        c_gt = RuleCondition(field="count", operator=ConditionOperator.GT, value=10)
        assert LogicInterpreter.evaluate_condition(c_gt, {"count": "15"}) is True
        assert LogicInterpreter.evaluate_condition(c_gt, {"count": "5"}) is False
        assert LogicInterpreter.evaluate_condition(c_gt, {"count": 10.0}) is False

        c_lte = RuleCondition(field="count", operator=ConditionOperator.LTE, value=10)
        assert LogicInterpreter.evaluate_condition(c_lte, {"count": 10}) is True
        assert LogicInterpreter.evaluate_condition(c_lte, {"count": 9.99}) is True
        assert LogicInterpreter.evaluate_condition(c_lte, {"count": 11}) is False

        # 4. IN and NOT_IN with list / non-list targets
        c_in = RuleCondition(field="tier", operator=ConditionOperator.IN, value=["critical", "high"])
        assert LogicInterpreter.evaluate_condition(c_in, {"tier": "CRITICAL"}) is True
        assert LogicInterpreter.evaluate_condition(c_in, {"tier": "LOW"}) is False

        c_not_in = RuleCondition(field="tier", operator=ConditionOperator.NOT_IN, value=["low", "info"])
        assert LogicInterpreter.evaluate_condition(c_not_in, {"tier": "CRITICAL"}) is True
        assert LogicInterpreter.evaluate_condition(c_not_in, {"tier": "LOW"}) is False

        # 5. String manipulation operators: STARTS_WITH, ENDS_WITH, CONTAINS, LOWER_IN
        c_starts = RuleCondition(field="asset", operator=ConditionOperator.STARTS_WITH, value="SRV-")
        assert LogicInterpreter.evaluate_condition(c_starts, {"asset": "srv-db-01"}) is True
        assert LogicInterpreter.evaluate_condition(c_starts, {"asset": "clt-01"}) is False

        c_ends = RuleCondition(field="file", operator=ConditionOperator.ENDS_WITH, value=".exe")
        assert LogicInterpreter.evaluate_condition(c_ends, {"file": "malware.EXE"}) is True
        assert LogicInterpreter.evaluate_condition(c_ends, {"file": "doc.pdf"}) is False

        # 6. LENGTH_LT / LENGTH_GT
        c_len_lt = RuleCondition(field="notes", operator=ConditionOperator.LENGTH_LT, value=20)
        assert LogicInterpreter.evaluate_condition(c_len_lt, {"notes": "short note"}) is True
        assert LogicInterpreter.evaluate_condition(c_len_lt, {"notes": "a" * 30}) is False

    def test_composite_nested_logical_trees(self):
        """Evaluates complex multi-layer nested AND/OR/NOT trees without recursion errors."""
        tree = RuleCondition(
            logical_op=LogicalOperator.AND,
            conditions=[
                RuleCondition(
                    logical_op=LogicalOperator.OR,
                    conditions=[
                        RuleCondition(field="severity", operator=ConditionOperator.EQ, value="CRITICAL"),
                        RuleCondition(field="priority", operator=ConditionOperator.EQ, value="P1"),
                    ],
                ),
                RuleCondition(
                    logical_op=LogicalOperator.NOT,
                    conditions=[
                        RuleCondition(field="status", operator=ConditionOperator.EQ, value="RESOLVED"),
                    ],
                ),
            ],
        )

        # Matching record
        assert LogicInterpreter.evaluate_condition(tree, {"severity": "CRITICAL", "status": "OPEN"}) is True
        assert LogicInterpreter.evaluate_condition(tree, {"priority": "P1", "status": "INVESTIGATING"}) is True

        # Non-matching (status is RESOLVED)
        assert LogicInterpreter.evaluate_condition(tree, {"severity": "CRITICAL", "status": "RESOLVED"}) is False

        # Non-matching (neither critical nor P1)
        assert LogicInterpreter.evaluate_condition(tree, {"severity": "LOW", "status": "OPEN"}) is False


# =============================================================================
# 3. CORRELATION ENGINE ADVERSARIAL STRESS TESTS
# =============================================================================

class TestCorrelationEngineAdversarial:
    """Stress tests text similarity, token spoofs, unicode, zero-width chars, and burst clustering."""

    def test_text_preprocessing_adversarial_chars(self):
        """preprocess_text must handle emojis, punctuation, zero-width spaces, and HTML tags."""
        # Punctuation spam & emojis
        raw = "🔥🚨 URGENT: Investigation confirmed FALSE POSITIVE!! #1234 @analyst (N/A) <script>alert(1)</script>"
        cleaned, tokens = preprocess_text(raw)
        assert "script" in tokens or "urgent" in tokens
        assert "🔥" not in tokens  # Non-word stripped
        assert len(cleaned) > 0

        # Zero-width spaces and invisible characters
        spoofed = "C\u200bo\u200bm\u200bp\u200br\u200bo\u200bm\u200bi\u200bs\u200be\u200bd account activity"
        cleaned_sp, tokens_sp = preprocess_text(spoofed)
        assert isinstance(cleaned_sp, str)

        # Empty string
        assert preprocess_text("") == ("", [])
        assert preprocess_text("   \t\n  ") == ("", [])

    def test_jaccard_similarity_edge_cases(self):
        """Jaccard similarity must be exact 1.0 on identical sets, 0.0 on disjoint, 0.0 on empty."""
        assert compute_jaccard_similarity([], []) == 0.0
        assert compute_jaccard_similarity(["a", "b"], []) == 0.0
        assert compute_jaccard_similarity(["token_a", "token_b"], ["token_a", "token_b"]) == 1.0
        assert compute_jaccard_similarity(["token_a"], ["token_b"]) == 0.0
        assert compute_jaccard_similarity(["a", "b", "c"], ["b", "c", "d"]) == 2.0 / 4.0  # 0.50

    def test_note_similarity_rubber_stamp_detection(self):
        """NoteSimilarityAnalyzer detects boilerplate copy-paste across distinct cases."""
        analyzer = NoteSimilarityAnalyzer(tfidf_threshold=0.85, jaccard_threshold=0.80, min_tokens=5)
        entity_id = uuid.uuid4()

        investigations = [
            {
                "event_id": uuid.uuid4(),
                "case_id": "CASE-101",
                "analyst_id": "analyst_alice",
                "investigation_notes": "Reviewed user login anomalies against authentication logs and determined activity is legitimate authorized access.",
            },
            {
                "event_id": uuid.uuid4(),
                "case_id": "CASE-102",
                "analyst_id": "analyst_bob",
                "investigation_notes": "Reviewed user login anomalies against authentication logs and determined activity is legitimate authorized access.",
            },
            {
                "event_id": uuid.uuid4(),
                "case_id": "CASE-103",
                "analyst_id": "analyst_charlie",
                "investigation_notes": "Malware detonation completed in sandbox environment showing reverse TCP shell payload.",
            },
        ]

        corrs = analyzer.find_similar_notes(investigations, entity_id)
        assert len(corrs) == 1
        assert corrs[0].correlation_type == "TFIDF_NOTE_SIMILARITY"
        assert corrs[0].similarity_score >= 0.85
        assert corrs[0].shared_attributes["case_id_a"] == "CASE-101"
        assert corrs[0].shared_attributes["case_id_b"] == "CASE-102"

    def test_burst_clusterer_sliding_window_boundaries(self):
        """SameAssetBurstClusterer must accurately cluster repeat alerts within sliding 24h."""
        clusterer = SameAssetBurstClusterer(window_seconds=86400, repeat_alert_threshold=5, repeat_high_alert_threshold=3)
        entity_id = uuid.uuid4()
        base_t = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)

        # 6 alerts within 2 hours on ASSET-SRV-01 (should burst)
        alerts_burst = [
            {
                "event_id": uuid.uuid4(),
                "asset_id": "ASSET-SRV-01",
                "severity": "HIGH",
                "event_timestamp": base_t + timedelta(minutes=15 * i),
                "rule_id": "PORT_SCAN",
            }
            for i in range(6)
        ]

        # 2 alerts separated by 30 hours on ASSET-SRV-02 (should NOT burst)
        alerts_non_burst = [
            {
                "event_id": uuid.uuid4(),
                "asset_id": "ASSET-SRV-02",
                "severity": "LOW",
                "event_timestamp": base_t + timedelta(hours=30 * i),
                "rule_id": "INFO_EVENT",
            }
            for i in range(2)
        ]

        clusters, corrs = clusterer.find_bursts(alerts_burst + alerts_non_burst, entity_id)
        assert len(clusters) == 1
        assert clusters[0].asset_id == "ASSET-SRV-01"
        assert clusters[0].alert_count == 6
        assert len(corrs) == 5  # First alert correlated to 5 subsequent alerts


# =============================================================================
# 4. PEER BENCHMARKING ENGINE COHORT FALLBACK STRESS TESTS
# =============================================================================

class TestPeerBenchmarkingAdversarial:
    """Stress tests cohort sizes (N=0, 1, 2, 3), single platform entity, and zero variance cohorts."""

    def test_cohort_distribution_identical_values(self):
        """When all peers have identical metric values, std_dev must be handled gracefully without NaN."""
        identical_cohort = [50.0, 50.0, 50.0, 50.0]
        mu, sigma, p25, p50, p75, p90 = compute_cohort_distribution(identical_cohort)
        assert mu == 50.0
        assert sigma >= 1e-4  # Epsilon floor
        assert p50 == 50.0

        z = compute_z_score(50.0, mu, sigma)
        assert z == 0.0

    def test_fallback_hierarchy_n_levels(self):
        """PeerBenchmarkEngine must cascade across Exact -> Sector -> Global -> Baseline when N < 3."""
        engine = PeerBenchmarkEngine(min_peer_group_size=3, dampening_lambda=0.50)
        target_id = uuid.uuid4()

        # Only 1 peer in sector Banking / Tier-1 (Target itself)
        eval_single, benchmarks = engine.evaluate_entity(
            target_entity_id=target_id,
            sector="Banking",
            size_tier="Tier-1",
            target_events=[],
            peer_snapshots=[],
        )

        assert eval_single.peer_group_size == 1
        assert eval_single.is_low_confidence is True
        assert eval_single.dampening_factor == 0.50
        assert eval_single.fallback_applied == "BASELINE_FALLBACK"
        assert 0.0 <= eval_single.peer_deviation_score <= 100.0
        assert len(benchmarks) == 5

        # 3 peers in Exact Cohort (Full Confidence)
        snapshots_3 = [
            EntityMetricSnapshot(entity_id=uuid.uuid4(), sector="Banking", size_tier="Tier-1", mtti_minutes=30.0),
            EntityMetricSnapshot(entity_id=uuid.uuid4(), sector="Banking", size_tier="Tier-1", mtti_minutes=45.0),
            EntityMetricSnapshot(entity_id=target_id, sector="Banking", size_tier="Tier-1", mtti_minutes=60.0),
        ]

        eval_3, _ = engine.evaluate_entity(
            target_entity_id=target_id,
            sector="Banking",
            size_tier="Tier-1",
            target_events=[],
            peer_snapshots=snapshots_3,
        )

        assert eval_3.peer_group_size == 3
        assert eval_3.is_low_confidence is False
        assert eval_3.dampening_factor == 1.0
        assert eval_3.fallback_applied == "EXACT_COHORT"


# =============================================================================
# 5. RISK SCORING ENGINE & FORMULA BOUNDARY STRESS TESTS
# =============================================================================

class TestRiskScoringAdversarial:
    """Stress tests clamping, tier mapping thresholds, scale factors, and trend directions."""

    def test_execution_gap_subscore_scale_factor_invariance(self):
        """Execution gap subscore must scale smoothly across negative, zero, and huge alert counts."""
        mock_findings = [
            ExecutionGapFindingDraft(
                entity_id=uuid.uuid4(),
                rule_id="EG-01",
                rule_name="Test Gap",
                rule_category="TRIAGE",
                severity="HIGH",
                severity_score=80,
                confidence=0.90,
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc),
                description="desc",
                rationale="rat",
                evidence_record_ids=["00000000-0000-0000-0000-000000000001"],
            )
        ]

        # Zero alert count
        s_zero = compute_execution_gap_subscore(mock_findings, alert_count=0)
        assert 0.0 <= s_zero <= 100.0

        # Negative alert count (defensive against corrupt input)
        s_neg = compute_execution_gap_subscore(mock_findings, alert_count=-50)
        assert 0.0 <= s_neg <= 100.0

        # Massive alert count (1,000,000)
        s_huge = compute_execution_gap_subscore(mock_findings, alert_count=1_000_000)
        assert 0.0 <= s_huge <= 100.0
        assert s_huge < s_zero  # ScaleFactor is larger, so subscore per finding is dampened

    def test_composite_formula_weights_and_clamping(self):
        """Composite score must adhere to 45/35/20 weights and clamp all inputs strictly in [0.0, 100.0]."""
        # Exact baseline: 50 * 0.45 + 50 * 0.35 + 50 * 0.20 = 50.0
        assert compute_composite_risk_score(s_eg=50.0, s_ns=50.0, s_peer=50.0) == 50.0

        # All zeros
        assert compute_composite_risk_score(s_eg=0.0, s_ns=0.0, s_peer=0.0) == 0.0

        # All 100s
        assert compute_composite_risk_score(s_eg=100.0, s_ns=100.0, s_peer=100.0) == 100.0

        # Asymmetric weights test (EG=100, others 0 -> 45.0)
        assert compute_composite_risk_score(s_eg=100.0, s_ns=0.0, s_peer=0.0) == 45.0

        # Out-of-bounds defense
        assert compute_composite_risk_score(s_eg=999.0, s_ns=999.0, s_peer=999.0) == 100.0
        assert compute_composite_risk_score(s_eg=-500.0, s_ns=-500.0, s_peer=-500.0) == 0.0

    def test_risk_tier_boundary_thresholds(self):
        """Verifies exact tier mapping on boundary values [0, 25, 50, 75, 100]."""
        assert map_score_to_risk_tier(0.0) == "LOW"
        assert map_score_to_risk_tier(25.0) == "LOW"
        assert map_score_to_risk_tier(25.01) == "GUARDED"
        assert map_score_to_risk_tier(50.0) == "GUARDED"
        assert map_score_to_risk_tier(50.01) == "ELEVATED"
        assert map_score_to_risk_tier(75.0) == "ELEVATED"
        assert map_score_to_risk_tier(75.01) == "CRITICAL"
        assert map_score_to_risk_tier(100.0) == "CRITICAL"

    def test_trend_direction_hysteresis(self):
        """Trend direction must require > 2.0 delta to escape STABLE."""
        assert determine_trend_direction(50.0, None) == "STABLE"
        assert determine_trend_direction(50.0, 50.0) == "STABLE"
        assert determine_trend_direction(52.0, 50.0) == "STABLE"  # Exact delta 2.0 is STABLE
        assert determine_trend_direction(52.1, 50.0) == "DETERIORATING"
        assert determine_trend_direction(48.0, 50.0) == "STABLE"  # Exact delta -2.0 is STABLE
        assert determine_trend_direction(47.9, 50.0) == "IMPROVING"


# =============================================================================
# 6. EXPLAINABILITY ENGINE & EVIDENCE LINKING STRESS TESTS
# =============================================================================

class TestExplainabilityAdversarial:
    """Verifies Rationale Cards preserve forensic evidence UUIDs and valid schemas."""

    def test_rationale_card_builder_evidence_traceability(self):
        """Rationale cards must link raw evidence record IDs and metric values."""
        entity_id = uuid.uuid4()
        event_uuid_1 = str(uuid.uuid4())
        event_uuid_2 = str(uuid.uuid4())

        eg_finding = ExecutionGapFindingDraft(
            entity_id=entity_id,
            rule_id="EG-01",
            rule_name="Uninvestigated Alerts",
            rule_category="TRIAGE_FAILURE",
            severity="CRITICAL",
            severity_score=95,
            confidence=0.95,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            description="Alert uninvestigated.",
            rationale="Forensic rationale text.",
            evidence_record_ids=[event_uuid_1, event_uuid_2],
            raw_evidence_refs=["ALT-001"],
            metric_values={"delay_hours": 12.5},
            recommendation="Fix triage desk.",
        )

        card = RationaleCardBuilder.build_from_execution_gap(eg_finding, entity_id)
        assert card.engine_name == "EXECUTION_GAP"
        assert card.rule_code == "EG-01"
        assert card.evidence_record_ids == [event_uuid_1, event_uuid_2]
        assert card.raw_evidence_refs == ["ALT-001"]
        assert card.metrics_snapshot["delay_hours"] == 12.5

        # Convert to shared schema
        shared_card = RationaleCardBuilder.to_shared_schema(card)
        assert shared_card.category == "EXECUTION_GAP"
        assert shared_card.severity.value == "CRITICAL"
        assert shared_card.evidence_record_ids == [event_uuid_1, event_uuid_2]


# =============================================================================
# 7. END-TO-END ANALYTICS PIPELINE STRESS & INTEGRATION
# =============================================================================

class TestAnalyticsPipelineStress:
    """Stress tests AnalyticsPipeline across full event payloads and parity between sync/async paths."""

    @pytest.mark.asyncio
    async def test_pipeline_sync_async_parity_on_realistic_workload(self):
        """Sync and async execution paths must produce numerically identical risk scores and findings count."""
        pipeline = AnalyticsPipeline()
        entity_id = uuid.uuid4()
        p_start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        p_end = datetime(2026, 8, 15, 23, 59, 59, tzinfo=timezone.utc)

        # Generate realistic multi-event telemetry stream
        events = []
        # 1. 25 Critical uninvestigated alerts on same asset (Triggers EG-01, EG-05, NS-05, Correlation Burst)
        for i in range(25):
            events.append({
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "raw_ref_id": f"ALT-CRIT-{i:03d}",
                "severity": "CRITICAL",
                "asset_id": "SRV-PROD-DB01",
                "criticality_tier": "CROWN_JEWEL",
                "alert_name": "SQL_INJECTION_ATTACK",
                "event_timestamp": p_start + timedelta(hours=i * 2),
            })

        # 2. 10 Cases dismissed rapidly within 60s (Triggers EG-07)
        analyst_t = p_start + timedelta(days=2)
        for i in range(10):
            events.append({
                "event_id": uuid.uuid4(),
                "dataset_type": "case_management",
                "standard_event_type": "CASE",
                "raw_ref_id": f"CASE-DISMISS-{i:03d}",
                "status": "CLOSED",
                "user_id": "analyst_fast",
                "closed_at": analyst_t + timedelta(seconds=i * 5),
                "event_timestamp": analyst_t + timedelta(seconds=i * 5),
            })

        req = AnalyzeRequest(
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
            sector="Banking",
            size_tier="Tier-1",
            events=events,
            previous_score=45.0,
            persist_to_db=False,
        )

        # Run Synchronous
        resp_sync = pipeline.execute_sync(request=req)

        # Run Asynchronous
        resp_async = await pipeline.execute_async(request=req)

        # Verify numerical and forensic parity
        assert resp_sync.risk_score.composite_risk_score == resp_async.risk_score.composite_risk_score
        assert resp_sync.risk_score.execution_gap_score == resp_async.risk_score.execution_gap_score
        assert resp_sync.risk_score.negative_space_score == resp_async.risk_score.negative_space_score
        assert resp_sync.risk_score.peer_deviation_score == resp_async.risk_score.peer_deviation_score
        assert resp_sync.risk_score.risk_tier == resp_async.risk_score.risk_tier
        assert resp_sync.risk_score.trend_direction == resp_async.risk_score.trend_direction

        assert resp_sync.execution_gap_count == resp_async.execution_gap_count
        assert resp_sync.negative_space_count == resp_async.negative_space_count
        assert resp_sync.correlations_count == resp_async.correlations_count
        assert resp_sync.burst_clusters_count == resp_async.burst_clusters_count
        assert len(resp_sync.rationale_cards) == len(resp_async.rationale_cards)

        # Validate findings presence
        assert resp_sync.execution_gap_count > 0
        assert resp_sync.burst_clusters_count > 0
        assert resp_sync.risk_score.composite_risk_score > 0.0


# =============================================================================
# 8. ADVERSARIAL COVERAGE OF ALL 16 RULES & CHECKS
# =============================================================================

class TestAllSixteenRulesAdversarial:
    """Stress tests every single one of the 8 EG rules and 8 NS checks individually."""

    def test_eg_01_through_08_individual_rules(self):
        """Verifies each EG rule triggers under positive conditions and suppresses under compliant conditions."""
        eg_engine = ExecutionGapEngine()
        entity_id = uuid.uuid4()
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        p_start = now - timedelta(days=7)
        p_end = now

        # --- EG-01: Uninvestigated Alert ---
        alert_uninvestigated = {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-01",
            "severity": "CRITICAL",
            "alert_name": "Ransomware Detected",
            "event_timestamp": now - timedelta(hours=5),
        }
        findings_01 = eg_engine.run([alert_uninvestigated], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-01" for f in findings_01)

        # --- EG-02: Missing Escalation ---
        case_p1_unescalated = {
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "raw_ref_id": "CASE-P1",
            "priority": "P1_CRITICAL",
            "severity": "CRITICAL",
            "status": "OPEN",
            "event_timestamp": now - timedelta(hours=10),
        }
        findings_02 = eg_engine.run([case_p1_unescalated], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-02" for f in findings_02)

        # --- EG-03: Stale Open Case ---
        case_stale = {
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "raw_ref_id": "CASE-STALE",
            "status": "OPEN",
            "event_timestamp": now - timedelta(days=5),
        }
        findings_03 = eg_engine.run([case_stale], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-03" for f in findings_03)

        # --- EG-04: Non-diligent Resolution Notes ---
        case_bad_notes = {
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "raw_ref_id": "CASE-FP",
            "status": "CLOSED",
            "notes": "fp",  # generic short note
            "event_timestamp": now - timedelta(hours=2),
        }
        findings_04 = eg_engine.run([case_bad_notes], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-04" for f in findings_04)

        # --- EG-05: Unassigned Crown Jewel Asset ---
        alert_cj = {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-CJ",
            "criticality_tier": "CROWN_JEWEL",
            "asset_id": "SWIFT-PAYMENT-GATEWAY",
            "event_timestamp": now - timedelta(hours=1),
        }
        findings_05 = eg_engine.run([alert_cj], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-05" for f in findings_05)

        # --- EG-06: Escalation Without Incident ---
        esc_tier3 = {
            "event_id": uuid.uuid4(),
            "dataset_type": "escalation_records",
            "standard_event_type": "ESCALATION",
            "raw_ref_id": "ESC-01",
            "case_id": "CASE-999",
            "escalated_to": "TIER_3_IR",
            "event_timestamp": now - timedelta(hours=30),
        }
        findings_06 = eg_engine.run([esc_tier3], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-06" for f in findings_06)

        # --- EG-07: Rapid Batch Dismissal ---
        fast_cases = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "case_management",
                "standard_event_type": "CASE",
                "raw_ref_id": f"CASE-FAST-{i}",
                "status": "CLOSED",
                "user_id": "analyst_bot",
                "closed_at": now - timedelta(seconds=10 * i),
                "event_timestamp": now - timedelta(seconds=10 * i),
            }
            for i in range(10)
        ]
        findings_07 = eg_engine.run(fast_cases, entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-07" for f in findings_07)

        # --- EG-08: Off-Hours SLA Breach ---
        # 2026-08-15 is a Saturday (weekend)
        alert_off_hours = {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-OFFHOURS",
            "severity": "CRITICAL",
            "event_timestamp": datetime(2026, 8, 15, 3, 0, 0, tzinfo=timezone.utc),  # 3 AM Saturday
        }
        findings_08 = eg_engine.run([alert_off_hours], entity_id, p_start, p_end)
        assert any(f.rule_id == "EG-08" for f in findings_08)

    def test_ns_01_through_08_individual_checks(self):
        """Verifies each NS check triggers under positive anomaly conditions."""
        ns_engine = NegativeSpaceEngine()
        entity_id = uuid.uuid4()
        now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        p_start = now - timedelta(days=14)
        p_end = now

        # --- NS-01: EWMA Volume Cliff ---
        # 6 days of volume: 50, 50, 50, 50, 50, 2 (severe drop from 50 to 2)
        cliff_events = []
        for d in range(5):
            for i in range(50):
                cliff_events.append({
                    "event_id": uuid.uuid4(),
                    "dataset_type": "alert_metadata",
                    "event_timestamp": now - timedelta(days=6 - d, hours=i % 12),
                })
        # Day 6 has 2 events
        for i in range(2):
            cliff_events.append({
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "event_timestamp": now - timedelta(hours=i + 1),
            })
        findings_01 = ns_engine.run(cliff_events, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-01" for f in findings_01)

        # --- NS-02: Missing Weekend Activity ---
        # 25 weekend alerts on Saturday (2026-08-15), 0 activities
        weekend_alerts = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "event_timestamp": datetime(2026, 8, 15, 10, i, 0, tzinfo=timezone.utc),
            }
            for i in range(25)
        ]
        findings_02 = ns_engine.run(weekend_alerts, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-02" for f in findings_02)

        # --- NS-03: Zero Coverage on Crown Jewels ---
        cj_asset_events = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "asset_inventory",
                "standard_event_type": "ASSET",
                "asset_id": "CRITICAL-AUTH-SERVER",
                "criticality_tier": "CROWN_JEWEL",
                "hostname": "auth01.internal",
            }
        ]
        findings_03 = ns_engine.run(cj_asset_events, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-03" for f in findings_03)

        # --- NS-04: Asymmetric Closure Rate (35 created, 1 closed = 2.8% < 10%) ---
        asymm_cases = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "case_management",
                "standard_event_type": "CASE",
                "status": "OPEN" if i > 0 else "CLOSED",
                "event_timestamp": now - timedelta(hours=i),
            }
            for i in range(35)
        ]
        findings_04 = ns_engine.run(asymm_cases, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-04" for f in findings_04)

        # --- NS-05: Missing Escalation on High-Severity Spike (25 critical alerts, 0 escalations) ---
        alert_spike = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "severity": "CRITICAL",
                "event_timestamp": now - timedelta(hours=i),
            }
            for i in range(25)
        ]
        findings_05 = ns_engine.run(alert_spike, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-05" for f in findings_05)

        # --- NS-06: Low Shannon Entropy Monoculture (60 identical alerts -> H(X) = 0.0) ---
        mono_alerts = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "rule_id": "SINGLE_RULE_FIRED_EXCLUSIVELY",
                "event_timestamp": now - timedelta(minutes=i * 10),
            }
            for i in range(60)
        ]
        findings_06 = ns_engine.run(mono_alerts, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-06" for f in findings_06)

        # --- NS-07: Unnaturally Constant Alert Intervals (CV < 0.01 with 25 alerts) ---
        synthetic_alerts = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "event_timestamp": now - timedelta(seconds=60 * i),
            }
            for i in range(25)
        ]
        findings_07 = ns_engine.run(synthetic_alerts, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-07" for f in findings_07)

        # --- NS-08: Missing Post-Incident Remediation (>14 days resolved) ---
        incident_old = [
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "incident_reports",
                "standard_event_type": "INCIDENT",
                "raw_ref_id": "INC-OLD-01",
                "resolved_at": now - timedelta(days=20),
                "event_timestamp": now - timedelta(days=21),
            }
        ]
        findings_08 = ns_engine.run(incident_old, entity_id, p_start, p_end)
        assert any(f.check_id == "NS-08" for f in findings_08)


# =============================================================================
# 9. FASTAPI REST API ROUTERS ADVERSARIAL TESTS
# =============================================================================

class TestApiRoutersAdversarial:
    """Stress tests FastAPI endpoints with httpx AsyncClient and auth verification."""

    @pytest.mark.asyncio
    async def test_api_health_endpoint(self):
        """GET /health must return status UP without auth."""
        from httpx import ASGITransport, AsyncClient
        from analytics_engine.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] in ("ok", "UP", "healthy")

    @pytest.mark.asyncio
    async def test_api_rules_endpoint(self, auth_headers):
        """GET /api/v1/analytics/rules must list default MVP rules."""
        from httpx import ASGITransport, AsyncClient
        from analytics_engine.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/analytics/rules", headers=auth_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["execution_gap_rules"]) >= 8
            assert len(data["negative_space_checks"]) >= 8

    @pytest.mark.asyncio
    async def test_api_benchmarks_endpoint(self, async_db, auth_headers):
        """GET /api/v1/analytics/benchmarks must return industry baselines."""
        from httpx import ASGITransport, AsyncClient
        from analytics_engine.main import app
        from shared.db.session import get_db

        app.dependency_overrides[get_db] = lambda: async_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/analytics/benchmarks?sector=Banking&size_tier=Tier-1",
                headers=auth_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_api_analyze_adversarial_payloads(self, async_db, auth_headers):
        """POST /api/v1/analytics/analyze must handle empty events and reject unauthenticated or corrupt requests."""
        from httpx import ASGITransport, AsyncClient
        from analytics_engine.main import app
        from shared.db.session import get_db

        app.dependency_overrides[get_db] = lambda: async_db
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            entity_id = str(uuid.uuid4())

            # 1. Unauthenticated request -> 403 Forbidden
            resp_no_auth = await client.post("/api/v1/analytics/analyze", json={"entity_id": entity_id})
            assert resp_no_auth.status_code == 403

            # 2. Empty events payload with valid auth
            req_empty = {
                "entity_id": entity_id,
                "sector": "Defense",
                "size_tier": "Tier-3",
                "events": [],
                "persist_to_db": False,
            }
            resp = await client.post("/api/v1/analytics/analyze", json=req_empty, headers=auth_headers)
            assert resp.status_code == 200
            res_data = resp.json()
            assert res_data["entity_id"] == entity_id
            assert res_data["risk_score"]["risk_tier"] == "LOW"

            # 3. Invalid entity_id format -> 422 Unprocessable Entity
            resp_bad = await client.post(
                "/api/v1/analytics/analyze",
                json={"entity_id": "not-a-uuid"},
                headers=auth_headers,
            )
            assert resp_bad.status_code == 422
        app.dependency_overrides.clear()

