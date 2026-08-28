"""Comprehensive Unit and Integration Test Suite for Synthetic Dataset Generator (Phase 6).

Tests:
1. Tier profile configurations and parameter distributions.
2. Gap injection mechanics for EG-01..EG-08, NS-01..NS-08, and correlation patterns.
3. Full dataset generation across all 8 dataset types.
4. Schema compatibility with CSVParser, JSONParser, RowValidator, and FieldMappingEngine.
5. End-to-end analytics engine evaluation on generated datasets.
6. Seed determinism and cryptographic manifest generation.
"""

from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import uuid

import pytest

from synthetic_data.tier_profiles import (
    QualityTier,
    TierProfileConfig,
    EntityProfile,
    HEALTHY_PROFILE,
    AVERAGE_PROFILE,
    WEAK_PROFILE,
    DEFAULT_ENTITIES,
    get_tier_profile,
)
from synthetic_data.gap_injector import (
    GapInjector,
    GroundTruthEntry,
    export_ground_truth_csv,
    export_ground_truth_json,
)
from synthetic_data.generator import (
    SyntheticDataGenerator,
    GeneratorConfig,
    GeneratedDatasetBundle,
)

import os
import sys

dp_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-processing")
if dp_root not in sys.path:
    sys.path.insert(0, dp_root)

# Imports from data-processing and analytics-engine
from shared.events.enums import DatasetType, StandardEventType
from app.parsers.csv_parser import CSVParser
from app.parsers.json_parser import JSONParser
from app.quarantine.validator import RowValidator
from app.mapping.engine import FieldMappingEngine

from analytics_engine import (
    ExecutionGapEngine,
    NegativeSpaceEngine,
    CorrelationEngine,
)


# =============================================================================
# 1. Tier Profile Tests
# =============================================================================

def test_tier_profiles_initialization_and_aliases():
    """Verifies all quality tier profiles and their alias lookups."""
    assert get_tier_profile("healthy").tier == QualityTier.HEALTHY
    assert get_tier_profile("HEALTHY").tier == QualityTier.HEALTHY
    assert get_tier_profile("tier-1").tier == QualityTier.HEALTHY
    assert get_tier_profile("Tier_1").tier == QualityTier.HEALTHY
    assert get_tier_profile("low").tier == QualityTier.HEALTHY

    assert get_tier_profile("average").tier == QualityTier.AVERAGE
    assert get_tier_profile("tier-2").tier == QualityTier.AVERAGE
    assert get_tier_profile("elevated").tier == QualityTier.AVERAGE

    assert get_tier_profile("weak").tier == QualityTier.WEAK
    assert get_tier_profile("tier-3").tier == QualityTier.WEAK
    assert get_tier_profile("critical").tier == QualityTier.WEAK

    with pytest.raises(ValueError):
        get_tier_profile("non_existent_tier")


def test_tier_profile_parameters_validity():
    """Verifies mathematical consistency of tier profile distributions."""
    for tier in [QualityTier.HEALTHY, QualityTier.AVERAGE, QualityTier.WEAK]:
        profile = get_tier_profile(tier)
        assert profile.alert_daily_mean > 0
        assert 0.0 <= profile.alert_triage_on_time_rate <= 1.0
        assert 0.0 <= profile.case_p1_escalation_rate <= 1.0
        assert 0.0 <= profile.case_stale_rate <= 1.0
        assert 0.0 <= profile.case_diligent_notes_rate <= 1.0
        assert 0.0 <= profile.crown_jewel_ratio <= 1.0
        assert 0.0 <= profile.crown_jewel_coverage_rate <= 1.0
        assert profile.expected_risk_score_range[0] < profile.expected_risk_score_range[1]

        # Verify severity distribution sums to ~1.0
        sev_sum = sum(profile.alert_severity_dist.values())
        assert abs(sev_sum - 1.0) < 1e-5


def test_default_entities_definitions():
    """Verifies default 10 predefined supervised entities."""
    assert len(DEFAULT_ENTITIES) == 10
    codes = [e.entity_code for e in DEFAULT_ENTITIES]
    assert len(codes) == len(set(codes)), "Entity codes must be unique"

    tiers = [e.quality_tier for e in DEFAULT_ENTITIES]
    assert QualityTier.HEALTHY in tiers
    assert QualityTier.AVERAGE in tiers
    assert QualityTier.WEAK in tiers


# =============================================================================
# 2. Gap Injector & Ground Truth Tests
# =============================================================================

def test_gap_injector_execution_and_negative_space():
    """Tests that GapInjector plants all required EG and NS ground truth entries on weak profile."""
    injector = GapInjector(seed=42)
    profile = WEAK_PROFILE
    start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2026, 3, 31, tzinfo=timezone.utc)

    # Initial dummy datasets
    datasets = {
        "alert_metadata": [],
        "case_management": [],
        "investigation_records": [],
        "escalation_records": [],
        "asset_inventory": [{"asset_id": "SRV-BASE", "hostname": "srv-base", "asset_type": "SERVER", "criticality_tier": "TIER_3"}],
        "incident_reports": [],
        "coverage_reports": [],
        "analyst_activity": [],
    }

    mutated_ds, ground_truth = injector.inject_gaps(
        datasets=datasets,
        profile=profile,
        entity_id="11111111-0008-4000-8000-000000000008",
        entity_code="ENT-008",
        period_name="2026-Q1",
        period_start=start_date,
        period_end=end_date,
    )

    gt_rules = {gt.rule_code for gt in ground_truth}

    # Check Execution Gaps planted
    assert "EG-01" in gt_rules
    assert "EG-02" in gt_rules
    assert "EG-03" in gt_rules
    assert "EG-04" in gt_rules
    assert "EG-05" in gt_rules
    assert "EG-06" in gt_rules
    assert "EG-07" in gt_rules
    assert "EG-08" in gt_rules

    # Check Negative Space Gaps planted
    assert "NS-01" in gt_rules
    assert "NS-02" in gt_rules
    assert "NS-03" in gt_rules
    assert "NS-04" in gt_rules
    assert "NS-05" in gt_rules
    assert "NS-06" in gt_rules
    assert "NS-07" in gt_rules
    assert "NS-08" in gt_rules

    # Check Correlation anomalies planted
    assert "CORR-BURST" in gt_rules
    assert "CORR-TEXT" in gt_rules


def test_ground_truth_export_csv_and_json():
    """Verifies that ground truth entries serialize cleanly to CSV and JSON."""
    entry = GroundTruthEntry(
        ground_truth_id=str(uuid.uuid4()),
        entity_id="11111111-0001-4000-8000-000000000001",
        entity_code="ENT-001",
        tier="healthy",
        period="2026-Q1",
        period_start="2026-01-01T00:00:00Z",
        period_end="2026-03-31T23:59:59Z",
        rule_code="EG-01",
        check_id="EG-01",
        target_dataset="alert_metadata",
        evidence_ids=["ALT-1001", "ALT-1002"],
        expected_severity="CRITICAL",
        timestamp="2026-01-15T12:00:00Z",
        description="Test description for uninvestigated alert.",
        injected_anomaly_details={"alert_id": "ALT-1001"},
    )

    csv_str = export_ground_truth_csv([entry])
    assert "ground_truth_id,entity_id,entity_code" in csv_str
    assert "EG-01" in csv_str
    assert "ALT-1001;ALT-1002" in csv_str

    json_str = export_ground_truth_json([entry])
    parsed_json = json.loads(json_str)
    assert len(parsed_json) == 1
    assert parsed_json[0]["rule_code"] == "EG-01"
    assert parsed_json[0]["evidence_ids"] == ["ALT-1001", "ALT-1002"]


# =============================================================================
# 3. Full Synthetic Dataset Generator Tests
# =============================================================================

def test_generator_all_8_datasets_generated():
    """Verifies generation of all 8 dataset types with non-empty compliant schemas."""
    config = GeneratorConfig(num_entities=3, periods=1, period_days=30, seed=42)
    generator = SyntheticDataGenerator(seed=42, config=config)
    bundle = generator.generate_all()

    assert len(bundle.entities) == 3
    assert len(bundle.entity_periods) == 3

    dataset_types = [
        "alert_metadata",
        "case_management",
        "investigation_records",
        "escalation_records",
        "asset_inventory",
        "incident_reports",
        "coverage_reports",
        "analyst_activity",
    ]

    for ep in bundle.entity_periods:
        for ds_name in dataset_types:
            assert ds_name in ep.datasets, f"Missing dataset {ds_name}"
            rows = ep.datasets[ds_name]
            assert isinstance(rows, list)
            assert len(rows) > 0, f"Dataset {ds_name} should not be empty for entity {ep.entity.entity_code}"


def test_generator_seed_reproducibility():
    """Verifies that identical seed produces byte-for-byte identical generated data."""
    config = GeneratorConfig(num_entities=2, periods=1, period_days=15, seed=12345)
    gen1 = SyntheticDataGenerator(seed=12345, config=config)
    bundle1 = gen1.generate_all()

    gen2 = SyntheticDataGenerator(seed=12345, config=config)
    bundle2 = gen2.generate_all()

    for ep1, ep2 in zip(bundle1.entity_periods, bundle2.entity_periods):
        for ds_name in ep1.datasets:
            assert ep1.datasets[ds_name] == ep2.datasets[ds_name], f"Mismatch in {ds_name} with same seed"


def test_generator_disk_export_and_manifest():
    """Verifies export to disk, folder layout, and cryptographic Merkle manifest creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = GeneratorConfig(
            num_entities=2,
            periods=1,
            period_days=15,
            seed=42,
            output_dir=temp_dir,
            output_format="all",
        )
        generator = SyntheticDataGenerator(seed=42, config=config)
        bundle = generator.generate_all()
        manifest = generator.export(bundle, output_dir=temp_dir)

        assert manifest["total_files"] > 0
        assert len(manifest["merkle_root"]) == 64  # SHA-256 hex string

        out_path = Path(temp_dir)
        assert (out_path / "manifest.json").exists()
        assert (out_path / "metadata" / "entities.json").exists()
        assert (out_path / "metadata" / "entities.csv").exists()
        assert (out_path / "metadata" / "ground_truth.json").exists()
        assert (out_path / "metadata" / "ground_truth.csv").exists()
        assert (out_path / "ground_truth.json").exists()
        assert (out_path / "ground_truth.csv").exists()


# =============================================================================
# 4. Ingestion, Quarantine, and Mapping Compatibility Tests
# =============================================================================

def test_csv_and_json_parser_compatibility():
    """Tests that generated CSV and JSON datasets parse cleanly with zero corruption."""
    generator = SyntheticDataGenerator(seed=42)
    entity = DEFAULT_ENTITIES[0]  # Healthy
    profile = HEALTHY_PROFILE
    ep_data = generator.generate_entity_period(
        entity=entity,
        profile=profile,
        period_name="2026-Q1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
    )

    # 1. Test CSV Parser
    csv_parser = CSVParser()
    for ds_name, rows in ep_data.datasets.items():
        csv_str = SyntheticDataGenerator._to_csv(rows)
        parsed_rows = list(csv_parser.parse_stream(io.BytesIO(csv_str.encode("utf-8"))))
        assert len(parsed_rows) == len(rows)
        for r in parsed_rows:
            assert not r.is_corrupted, f"Corrupted CSV row in {ds_name}: {r.corruption_reason}"

    # 2. Test JSON Parser
    json_parser = JSONParser()
    for ds_name, rows in ep_data.datasets.items():
        json_str = json.dumps(rows)
        parsed_rows = list(json_parser.parse_stream(io.BytesIO(json_str.encode("utf-8"))))
        assert len(parsed_rows) == len(rows)
        for r in parsed_rows:
            assert not r.is_corrupted, f"Corrupted JSON row in {ds_name}: {r.corruption_reason}"


def test_quarantine_validator_and_mapping_engine_compatibility():
    """Tests that generated normal rows pass RowValidator and normalize properly, while decoy rows are quarantined."""
    generator = SyntheticDataGenerator(seed=42)
    entity = DEFAULT_ENTITIES[0]
    profile = HEALTHY_PROFILE
    ep_data = generator.generate_entity_period(
        entity=entity,
        profile=profile,
        period_name="2026-Q1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
    )

    for ds_name, rows in ep_data.datasets.items():
        validator = RowValidator(dataset_type=ds_name)
        mapping_engine = FieldMappingEngine(dataset_type=ds_name)

        for idx, row in enumerate(rows):
            from app.parsers.base import ParsedRow
            parsed_row = ParsedRow(row_index=idx, data=row)
            failure = validator.validate_parsed_row(parsed_row)

            # Check if this row is an intentional quarantine decoy
            is_decoy = (
                (ds_name == "alert_metadata" and row.get("alert_id") is None)
                or (ds_name == "case_management" and "INVALID_DATE" in str(row.get("created_at")))
                or (ds_name == "coverage_reports" and row.get("uptime_pct") == "CORRUPTED_NOT_A_FLOAT")
            )

            if is_decoy:
                assert failure is not None, f"Decoy row in {ds_name} was expected to fail validation but passed!"
            else:
                assert failure is None, f"Row validation failure in {ds_name} (row {idx}): {failure.message if failure else ''}"
                # Verify Normalization on valid rows
                normalized = mapping_engine.normalize_record(row, row_index=idx)
                assert normalized["dataset_type"] == ds_name
                assert normalized["event_timestamp"] is not None
                assert normalized["raw_ref_id"] is not None or ds_name == "asset_inventory"


def test_synthetic_data_analytics_engines_evaluation():
    """Tests that normalized synthetic data from a weak entity triggers all analytics engines."""
    generator = SyntheticDataGenerator(seed=42)
    entity = DEFAULT_ENTITIES[7]  # ENT-008 (Weak)
    profile = WEAK_PROFILE
    period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(2026, 3, 31, tzinfo=timezone.utc)

    ep_data = generator.generate_entity_period(
        entity=entity,
        profile=profile,
        period_name="2026-Q1",
        period_start=period_start,
        period_end=period_end,
    )

    # Normalize all datasets into event dictionaries for the engines
    all_normalized_events = []
    for ds_name, rows in ep_data.datasets.items():
        mapping_engine = FieldMappingEngine(dataset_type=ds_name)
        for idx, row in enumerate(rows):
            # Skip invalid decoys for engine test
            if row.get("alert_id") is None and ds_name == "alert_metadata":
                continue
            if "INVALID_DATE" in str(row.get("created_at")):
                continue
            if row.get("uptime_pct") == "CORRUPTED_NOT_A_FLOAT":
                continue

            normalized = mapping_engine.normalize_record(row, row_index=idx)
            normalized["event_id"] = uuid.uuid4()
            all_normalized_events.append(normalized)

    # 1. Execution Gap Engine
    eg_engine = ExecutionGapEngine()
    eg_findings = eg_engine.run(
        events=all_normalized_events,
        entity_id=uuid.UUID(entity.entity_id),
        period_start=period_start,
        period_end=period_end,
    )
    assert len(eg_findings) > 0
    eg_rules_found = {f.rule_id for f in eg_findings}
    # Weak entity should trigger multiple execution gap rules
    assert "EG-01" in eg_rules_found or "EG-03" in eg_rules_found or "EG-04" in eg_rules_found

    # 2. Negative Space Engine
    ns_engine = NegativeSpaceEngine()
    ns_findings = ns_engine.run(
        events=all_normalized_events,
        entity_id=uuid.UUID(entity.entity_id),
        period_start=period_start,
        period_end=period_end,
    )
    assert len(ns_findings) > 0
    ns_checks_found = {f.check_id for f in ns_findings}
    assert len(ns_checks_found) >= 1

    # 3. Correlation Engine
    corr_engine = CorrelationEngine()
    correlations, clusters = corr_engine.run(
        events=all_normalized_events,
        entity_id=uuid.UUID(entity.entity_id),
        period_start=period_start,
        period_end=period_end,
    )
    # Check that correlation engine detected bursts and/or note clones
    assert len(correlations) > 0 or len(clusters) > 0

