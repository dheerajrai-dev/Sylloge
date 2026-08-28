"""Unit tests for Peer Benchmarking Engine, Cohort Segmentation, and Fallbacks."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from analytics_engine.engines.peer_benchmark.engine import PeerBenchmarkEngine
from analytics_engine.engines.peer_benchmark.metrics import extract_entity_metrics
from analytics_engine.engines.peer_benchmark.models import EntityMetricSnapshot
from analytics_engine.engines.peer_benchmark.stats import (
    compute_cohort_distribution,
    compute_ecdf_percentile,
    compute_z_score,
)


def test_distribution_and_zscore_math():
    """Verifies sample statistics, Z-score, and ECDF percentiles."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    mean, std_dev, p25, p50, p75, p90 = compute_cohort_distribution(values)

    assert mean == 30.0
    assert round(std_dev, 2) == 15.81
    assert p50 == 30.0

    # Z-Score of 50.0 with mean 30.0, std 15.8114
    z = compute_z_score(50.0, mean, std_dev)
    assert round(z, 2) == 1.26

    # ECDF percentile of 30.0 in [10, 20, 30, 40, 50] -> (2 strictly less + 0.5 equal)/5 = 2.5/5 = 50%
    pct = compute_ecdf_percentile(30.0, values)
    assert pct == 50.0


def test_metrics_extraction(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies extraction of the 5 supervisory metrics from events."""
    events = [
        # 4 alerts
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-1",
            "event_timestamp": sample_now - timedelta(minutes=60),
        },
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-2",
            "event_timestamp": sample_now - timedelta(minutes=40),
        },
        # 1 investigation 20 minutes after ALT-1
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "investigation_records",
            "standard_event_type": "INVESTIGATION",
            "raw_ref_id": "ALT-1",
            "event_timestamp": sample_now - timedelta(minutes=40),
        },
        # 1 escalation
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "escalation_records",
            "standard_event_type": "ESCALATION",
            "event_timestamp": sample_now - timedelta(minutes=30),
        },
        # 2 cases
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "status": "OPEN",
            "event_timestamp": sample_now - timedelta(days=5),  # Stale case (>72h)
        },
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "status": "CLOSED",
            "event_timestamp": sample_now - timedelta(hours=2),
        },
        # 1 crown jewel asset without coverage
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "asset_inventory",
            "standard_event_type": "ASSET",
            "asset_id": "CJ-DB",
            "criticality_tier": "CROWN_JEWEL",
        },
    ]

    snapshot = extract_entity_metrics(
        entity_id=entity_id,
        sector="Banking",
        size_tier="Tier-1",
        events=events,
        execution_gap_findings=[{"id": 1}],
    )

    assert snapshot.mtti_minutes == 20.0
    assert snapshot.escalation_rate == 0.50  # 1 esc / 2 alerts
    assert snapshot.stale_case_ratio == 0.50  # 1 stale / 2 cases
    assert snapshot.coverage_gap_ratio == 1.0  # 1 unmonitored / 1 crown jewel
    assert snapshot.execution_gap_rate == 50.0  # 1 finding / 2 cases * 100


def test_peer_benchmark_with_full_cohort(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies peer benchmarking with full cohort size >= 3."""
    engine = PeerBenchmarkEngine(min_peer_group_size=3)

    # 4 peer snapshots in Banking Tier-1
    peers = [
        EntityMetricSnapshot(
            entity_id=uuid.uuid4(),
            sector="Banking",
            size_tier="Tier-1",
            mtti_minutes=25.0,
            escalation_rate=0.08,
            stale_case_ratio=0.04,
            coverage_gap_ratio=0.02,
            execution_gap_rate=2.0,
        ),
        EntityMetricSnapshot(
            entity_id=uuid.uuid4(),
            sector="Banking",
            size_tier="Tier-1",
            mtti_minutes=35.0,
            escalation_rate=0.07,
            stale_case_ratio=0.06,
            coverage_gap_ratio=0.03,
            execution_gap_rate=2.5,
        ),
        EntityMetricSnapshot(
            entity_id=uuid.uuid4(),
            sector="Banking",
            size_tier="Tier-1",
            mtti_minutes=30.0,
            escalation_rate=0.09,
            stale_case_ratio=0.05,
            coverage_gap_ratio=0.01,
            execution_gap_rate=1.8,
        ),
    ]

    events = [
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "event_timestamp": sample_now,
        }
    ]

    evaluation, benchmarks = engine.evaluate_entity(
        target_entity_id=entity_id,
        sector="Banking",
        size_tier="Tier-1",
        target_events=events,
        peer_snapshots=peers,
    )

    assert evaluation.is_low_confidence is False
    assert evaluation.dampening_factor == 1.0
    assert evaluation.fallback_applied == "EXACT_COHORT"
    assert len(benchmarks) == 5


def test_peer_benchmark_low_confidence_fallback(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies fallback and 0.50 dampening when exact cohort has N < 3."""
    engine = PeerBenchmarkEngine(min_peer_group_size=3, dampening_lambda=0.50)

    # Only 1 peer exists (N=2 with target < 3)
    peers = [
        EntityMetricSnapshot(
            entity_id=uuid.uuid4(),
            sector="Energy",
            size_tier="Tier-3",
            mtti_minutes=60.0,
            escalation_rate=0.05,
            stale_case_ratio=0.10,
            coverage_gap_ratio=0.05,
            execution_gap_rate=3.0,
        )
    ]

    events = [
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "event_timestamp": sample_now,
        }
    ]

    evaluation, benchmarks = engine.evaluate_entity(
        target_entity_id=entity_id,
        sector="Energy",
        size_tier="Tier-3",
        target_events=events,
        peer_snapshots=peers,
    )

    assert evaluation.is_low_confidence is True
    assert evaluation.dampening_factor == 0.50
    assert evaluation.fallback_applied in ("BASELINE_FALLBACK", "GLOBAL_FALLBACK", "SECTOR_FALLBACK")
    for b in benchmarks:
        assert b.is_low_confidence is True
