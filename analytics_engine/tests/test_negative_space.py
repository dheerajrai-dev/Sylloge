"""Unit tests for Negative Space Engine, Statistical Models, and Graceful Degradation."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from analytics_engine.engines.negative_space.engine import NegativeSpaceEngine
from analytics_engine.engines.negative_space.stats import (
    compute_ewma_baseline,
    compute_inter_arrival_cv,
    compute_low_volume_degradation,
    compute_shannon_entropy,
    detect_ewma_volume_cliff,
)


def test_ewma_math_and_cliff_detector():
    """Verifies EWMA recurrence and cliff anomaly detection."""
    # 10 days of stable volume ~ 1000 events/day, then sudden cliff to 50 events
    stable_volumes = [1000.0] * 10
    mu, sigma = compute_ewma_baseline(stable_volumes, alpha=0.20)
    assert 990.0 <= mu <= 1010.0
    assert sigma <= 1.0

    cliff_volumes = [1000.0] * 10 + [50.0]
    cliff_res = detect_ewma_volume_cliff(cliff_volumes, alpha=0.20, k=3.0)
    assert cliff_res is not None
    assert cliff_res["observed_volume"] == 50.0
    assert cliff_res["drop_percentage"] >= 90.0


def test_shannon_entropy_math():
    """Verifies Categorical Shannon entropy calculations."""
    # Case 1: Pure monoculture (100 alerts, all same rule)
    monoculture = ["RULE_SAME"] * 100
    h_mono, max_h, n, m = compute_shannon_entropy(monoculture)
    assert h_mono == 0.0
    assert m == 1

    # Case 2: Uniform distribution (100 alerts evenly split across 4 rules)
    uniform = ["RULE_A", "RULE_B", "RULE_C", "RULE_D"] * 25
    h_uni, max_h, n, m = compute_shannon_entropy(uniform)
    assert round(h_uni, 2) == 2.0  # -4 * (0.25 * log2(0.25)) = 2.0 bits


def test_inter_arrival_cv_math(sample_now: datetime):
    """Verifies CV calculation for natural vs synthetic constant intervals."""
    # Synthetic: strictly 10.0 seconds between every alert
    synthetic_times = [sample_now + timedelta(seconds=i * 10) for i in range(30)]
    cv_synth, mu_delta, sigma_delta, n = compute_inter_arrival_cv(synthetic_times)
    assert cv_synth < 0.001
    assert round(mu_delta, 1) == 10.0
    assert round(sigma_delta, 2) == 0.0

    # Natural / Random: variable arrival times
    natural_deltas = [2, 18, 5, 45, 12, 8, 90, 3, 22, 14, 55, 6, 31, 10, 4, 60, 11, 25, 7, 33]
    t = sample_now
    natural_times = [t]
    for d in natural_deltas:
        t += timedelta(seconds=d)
        natural_times.append(t)

    cv_nat, mu_d, sigma_d, n = compute_inter_arrival_cv(natural_times)
    assert cv_nat > 0.50


def test_low_volume_graceful_degradation():
    """Verifies confidence dampening when sample count N < 15."""
    w_full, is_deg_full = compute_low_volume_degradation(n=50, n_min=15)
    assert w_full == 1.0
    assert is_deg_full is False

    w_deg, is_deg = compute_low_volume_degradation(n=3, n_min=15)
    assert round(w_deg, 2) == 0.20
    assert is_deg is True


def test_ns_01_ewma_cliff(entity_id: uuid.UUID, sample_now: datetime):
    """NS-01: Verifies volume cliff check on event stream."""
    engine = NegativeSpaceEngine()

    events = []
    # 9 days of 50 events/day
    for day in range(9):
        day_t = datetime(2026, 8, 10 + day, 8, 0, 0, tzinfo=timezone.utc)
        for i in range(50):
            events.append({
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "event_timestamp": day_t + timedelta(minutes=i * 10),
            })

    # Day 10: cliff to only 2 events
    day_10 = datetime(2026, 8, 19, 8, 0, 0, tzinfo=timezone.utc)
    events.append({
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "event_timestamp": day_10 + timedelta(minutes=30),
    })
    events.append({
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "event_timestamp": day_10 + timedelta(minutes=60),
    })

    p_start = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)
    p_end = datetime(2026, 8, 19, 23, 59, 59, tzinfo=timezone.utc)
    findings = engine.run(events, entity_id, p_start, p_end)
    ns01 = [f for f in findings if f.check_id == "NS-01"]
    assert len(ns01) == 1
    assert ns01[0].drop_percentage >= 80.0


def test_ns_02_missing_weekend_activity(entity_id: uuid.UUID):
    """NS-02: Verifies weekend alerts >= 20 without analyst activity triggers finding."""
    engine = NegativeSpaceEngine()

    # Saturday UTC
    saturday = datetime(2026, 8, 22, 10, 0, 0, tzinfo=timezone.utc)
    sunday_end = datetime(2026, 8, 23, 23, 59, 59, tzinfo=timezone.utc)

    # 25 weekend alerts, 0 activity logs
    events = []
    for i in range(25):
        events.append({
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "event_timestamp": saturday + timedelta(hours=i),
        })

    findings = engine.run(events, entity_id, saturday, sunday_end)
    ns02 = [f for f in findings if f.check_id == "NS-02"]
    assert len(ns02) == 1
    assert ns02[0].observed_volume == 0.0
    assert ns02[0].drop_percentage == 100.0


def test_ns_03_zero_coverage_crown_jewel(entity_id: uuid.UUID, sample_now: datetime):
    """NS-03: Verifies unmonitored Crown Jewel asset triggers finding."""
    engine = NegativeSpaceEngine()

    events = [
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "asset_inventory",
            "standard_event_type": "ASSET",
            "asset_id": "CJ-PAYMENT-GATEWAY",
            "criticality_tier": "CROWN_JEWEL",
            "hostname": "payment-gw.bank.internal",
        },
        # Coverage report with 0 uptime or missing
    ]

    findings = engine.run(events, entity_id, sample_now - timedelta(days=1), sample_now)
    ns03 = [f for f in findings if f.check_id == "NS-03"]
    assert len(ns03) == 1
    assert ns03[0].severity == "CRITICAL"


def test_ns_06_low_entropy_monoculture(entity_id: uuid.UUID, sample_now: datetime):
    """NS-06: Verifies monoculture alerts entropy H(X) < 0.50 triggers finding."""
    engine = NegativeSpaceEngine()

    # 60 alerts, 59 with SAME_RULE and 1 with OTHER_RULE
    events = []
    for i in range(59):
        events.append({
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "rule_id": "ONLY_SSH_AUTH_FAIL",
            "event_timestamp": sample_now - timedelta(minutes=i * 5),
        })
    events.append({
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "rule_id": "OTHER_RULE",
        "event_timestamp": sample_now - timedelta(minutes=300),
    })

    findings = engine.run(events, entity_id, sample_now - timedelta(days=1), sample_now)
    ns06 = [f for f in findings if f.check_id == "NS-06"]
    assert len(ns06) == 1
    assert ns06[0].entropy_score is not None
    assert ns06[0].entropy_score < 0.50


def test_ns_07_synthetic_heartbeat_cv(entity_id: uuid.UUID, sample_now: datetime):
    """NS-07: Verifies inter-arrival CV < 0.01 triggers synthetic heartbeat finding."""
    engine = NegativeSpaceEngine()

    events = []
    for i in range(25):
        events.append({
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "event_timestamp": sample_now - timedelta(seconds=i * 60),  # Exactly 60s
        })

    findings = engine.run(events, entity_id, sample_now - timedelta(hours=1), sample_now)
    ns07 = [f for f in findings if f.check_id == "NS-07"]
    assert len(ns07) == 1
    assert ns07[0].observed_volume < 0.01
