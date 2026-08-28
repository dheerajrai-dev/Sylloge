"""Empirical Adversarial Challenge and Stress Test Suite for Milestone 2.

Tests stream parsers, quarantine validator edge cases, field mapping & normalizer
transformations, and full ingestion pipeline resilience under hostile/corrupt data.
"""

import datetime
import io
import json
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.events.enums import DatasetType, SeverityTier, StandardEventType, SubmissionStatus
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.mapping import FieldMappingProfile
from shared.models.quarantine import QuarantinedRow
from shared.models.submission import RawSubmission

import sys
import os
dp_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data-processing")
if dp_root not in sys.path:
    sys.path.insert(0, dp_root)

from app.parsers.base import BaseParser, ParsedRow
from app.parsers import (
    get_parser_for_dataset,
    CSVParser,
    JSONParser,
    AlertMetadataParser,
    CaseManagementParser,
    InvestigationRecordParser,
    EscalationRecordParser,
    AssetInventoryParser,
    IncidentReportParser,
    CoverageReportParser,
    AnalystActivityParser,
)
from app.quarantine.errors import QuarantineErrorCode, RowValidationFailure
from app.quarantine.validator import RowValidator
from app.quarantine.manager import QuarantineManager
from app.mapping.transforms import (
    cast_boolean,
    normalize_severity,
    normalize_status,
    parse_timestamp,
)
from app.mapping.defaults import CANONICAL_FIELD_ALIASES, DATASET_TO_EVENT_TYPE, get_standard_event_type
from app.mapping.engine import FieldMappingEngine
from app.mapping.normalizer import CanonicalNormalizer
from app.pipeline.ingestion_service import IngestionPipelineService


# ============================================================================
# 1. PARSER ADVERSARIAL & EDGE CASE SUITE
# ============================================================================

def test_parser_empty_and_whitespace_inputs():
    """Verify parsers handle empty strings, whitespace, empty bytes cleanly without crashing."""
    parsers = [
        CSVParser(),
        JSONParser(),
        AlertMetadataParser(),
        CaseManagementParser(),
        InvestigationRecordParser(),
        EscalationRecordParser(),
        AssetInventoryParser(),
        IncidentReportParser(),
        CoverageReportParser(),
        AnalystActivityParser(),
    ]
    for p in parsers:
        assert list(p.parse_stream("")) == []
        assert list(p.parse_stream("   \n\t\r\n  ")) == []
        assert list(p.parse_stream(b"")) == []
        assert list(p.parse_stream(io.StringIO(""))) == []
        assert list(p.parse_stream(io.BytesIO(b""))) == []


def test_csv_parser_mixed_delimiters_and_quotes():
    """Verify CSV parser correctly handles tabs, semicolons, quotes containing delimiters, and escaped characters."""
    # Semicolon delimited with quoted values
    csv_semi = (
        'alert_id;rule_name;details\n'
        'ALT-1;"Suspicious; Activity";"Found \\"malware\\" on host"\n'
        'ALT-2;Normal;Clean\n'
    )
    rows = list(CSVParser().parse_stream(csv_semi))
    assert len(rows) == 2
    assert rows[0].data["alert_id"] == "ALT-1"
    assert rows[0].data["rule_name"] == "Suspicious; Activity"
    assert not rows[0].is_corrupted

    # Tab delimited with empty cells
    tsv_data = "case_id\tstatus\tnotes\nCASE-99\tOPEN\t\n"
    rows_tsv = list(CSVParser().parse_stream(tsv_data))
    assert len(rows_tsv) == 1
    assert rows_tsv[0].data["case_id"] == "CASE-99"
    assert rows_tsv[0].data["status"] == "OPEN"
    assert rows_tsv[0].data["notes"] is None


def test_csv_parser_jagged_rows_flagged_as_corrupted():
    """Verify rows with too few or too many columns are flagged as corrupted with exact reasons."""
    jagged_csv = (
        "id,name,value\n"
        "1,alpha,100\n"
        "2,beta\n"  # Missing column
        "3,gamma,300,EXTRA1,EXTRA2\n"  # Extra columns
        "4,delta,400\n"
    )
    rows = list(CSVParser().parse_stream(jagged_csv))
    assert len(rows) == 4
    assert not rows[0].is_corrupted
    assert rows[1].is_corrupted
    assert "Column count mismatch" in rows[1].corruption_reason
    assert rows[1].data["value"] is None
    assert rows[2].is_corrupted
    assert "__extra__" in rows[2].data
    assert rows[2].data["__extra__"] == ["EXTRA1", "EXTRA2"]
    assert not rows[3].is_corrupted


def test_json_parser_diverse_wrappers_and_ndjson():
    """Verify JSON parser extracts records from diverse wrapper objects and mixed NDJSON."""
    # Custom wrapper key 'alerts'
    data_alerts = json.dumps({"alerts": [{"alert_id": "A1"}, {"alert_id": "A2"}]})
    rows = list(JSONParser().parse_stream(data_alerts))
    assert len(rows) == 2
    assert rows[0].data["alert_id"] == "A1"

    # Custom wrapper key 'events'
    data_events = json.dumps({"events": [{"event_id": "E1"}]})
    rows = list(JSONParser().parse_stream(data_events))
    assert len(rows) == 1
    assert rows[0].data["event_id"] == "E1"

    # Mixed NDJSON with non-dict elements
    ndjson_mixed = (
        '{"alert_id": "OK-1"}\n'
        '"just a string item"\n'
        '12345\n'
        '{"alert_id": "OK-2"}\n'
        'CORRUPT_JSON_SYNTAX{\n'
    )
    rows_nd = list(JSONParser().parse_stream(ndjson_mixed))
    assert len(rows_nd) == 5
    assert not rows_nd[0].is_corrupted and rows_nd[0].data["alert_id"] == "OK-1"
    assert rows_nd[1].is_corrupted
    assert rows_nd[2].is_corrupted
    assert not rows_nd[3].is_corrupted and rows_nd[3].data["alert_id"] == "OK-2"
    assert rows_nd[4].is_corrupted


# ============================================================================
# 2. QUARANTINE VALIDATOR & ERROR CODE CLASSIFICATION SUITE
# ============================================================================

@pytest.mark.parametrize("dataset_type,missing_payload,expected_failed_field", [
    (DatasetType.ALERT_METADATA, {"severity": "HIGH"}, "alert_id"),
    (DatasetType.CASE_MANAGEMENT, {"status": "OPEN"}, "case_id"),
    (DatasetType.INVESTIGATION_RECORDS, {"action_taken": "Investigate"}, "investigation_id"),
    (DatasetType.ESCALATION_RECORDS, {"escalated_to": "SOC"}, "escalation_id"),
    (DatasetType.ASSET_INVENTORY, {"criticality": "HIGH"}, "asset_id"),
    (DatasetType.INCIDENT_REPORTS, {"root_cause": "Phishing"}, "incident_id"),
    (DatasetType.COVERAGE_REPORTS, {"uptime_pct": 99.0}, "coverage_id"),
    (DatasetType.ANALYST_ACTIVITY, {"activity_type": "LOGIN"}, "activity_id"),
])
def test_validator_mandatory_primary_key_failures(dataset_type, missing_payload, expected_failed_field):
    """Verify validator flags missing primary keys across all 8 dataset types."""
    validator = RowValidator(dataset_type)
    row = ParsedRow(row_index=1, data=missing_payload)
    fail = validator.validate_parsed_row(row)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.MISSING_REQUIRED_FIELD
    assert expected_failed_field in fail.failed_fields


def test_validator_timestamp_fuzzing():
    """Verify validator accepts valid timestamp variants and catches bad ones."""
    validator = RowValidator(DatasetType.ALERT_METADATA)

    valid_timestamps = [
        "2026-08-25T12:00:00Z",
        "2026-08-25T12:00:00+00:00",
        "2026-08-25 12:00:00",
        "2026-08-25",
        "25/08/2026 12:00:00",
        "08/25/2026 12:00:00",
        1787668200,
        1787668200000,
        "1787668200",
        datetime.datetime.now(datetime.timezone.utc),
    ]
    for idx, ts in enumerate(valid_timestamps, start=1):
        row = ParsedRow(row_index=idx, data={"alert_id": f"A-{idx}", "timestamp": ts})
        assert validator.validate_parsed_row(row) is None, f"Failed on valid timestamp: {ts}"

    invalid_timestamps = [
        "not_a_date",
        "2026-99-99",
        "invalid_timestamp_12345",
        "abc-def-ghij",
    ]
    for idx, ts in enumerate(invalid_timestamps, start=100):
        row = ParsedRow(row_index=idx, data={"alert_id": f"A-{idx}", "timestamp": ts})
        fail = validator.validate_parsed_row(row)
        assert fail is not None
        assert fail.error_code == QuarantineErrorCode.DATETIME_PARSE_ERROR


def test_validator_numeric_field_fuzzing():
    """Verify validator flags invalid numeric types in numeric fields."""
    validator = RowValidator(DatasetType.COVERAGE_REPORTS)

    # Valid numeric
    row_valid = ParsedRow(
        row_index=1,
        data={"coverage_id": "C-1", "reported_at": "2026-08-25T00:00:00Z", "uptime_pct": "99.9", "event_count": 1000},
    )
    assert validator.validate_parsed_row(row_valid) is None

    # Invalid numeric strings
    row_bad_uptime = ParsedRow(
        row_index=2,
        data={"coverage_id": "C-2", "reported_at": "2026-08-25T00:00:00Z", "uptime_pct": "NINETY_NINE"},
    )
    fail = validator.validate_parsed_row(row_bad_uptime)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.TYPE_MISMATCH
    assert "uptime_pct" in fail.failed_fields


def test_validator_batch_duplicate_primary_key():
    """Verify duplicate primary key within same batch is flagged."""
    validator = RowValidator(DatasetType.ALERT_METADATA)

    row1 = ParsedRow(row_index=1, data={"alert_id": "DUP-1", "timestamp": "2026-08-25T10:00:00Z"})
    assert validator.validate_parsed_row(row1) is None

    row2 = ParsedRow(row_index=2, data={"alert_id": "DUP-1", "timestamp": "2026-08-25T10:05:00Z"})
    fail = validator.validate_parsed_row(row2)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.DUPLICATE_PRIMARY_KEY


# ============================================================================
# 3. QUARANTINE MANAGER INVARIANTS & PRESERVATION
# ============================================================================

def test_quarantine_manager_preserves_exact_raw_content():
    """Verify quarantine manager faithfully stores original raw payload without mutation."""
    sub_id = uuid.uuid4()
    ent_id = uuid.uuid4()
    mgr = QuarantineManager(submission_id=sub_id, entity_id=ent_id, dataset_type=DatasetType.ALERT_METADATA)

    raw_payload = {"alert_id": None, "original_field": "unaltered_value", "nested": {"k": 123}}
    failure = RowValidationFailure(
        error_code=QuarantineErrorCode.MISSING_REQUIRED_FIELD,
        message="Missing alert_id",
        failed_fields=["alert_id"],
        raw_data=raw_payload,
        row_index=7,
    )
    q_row = mgr.record_failure(failure)

    assert q_row.raw_content == raw_payload
    assert q_row.row_index == 7
    assert "MISSING_REQUIRED_FIELD" in q_row.failure_reason

    # Verify JSON export
    dump = mgr.export_dump_payload()
    assert dump["total_quarantined"] == 1
    assert dump["rows"][0]["raw_content"] == raw_payload


# ============================================================================
# 4. FIELD MAPPING ENGINE & NORMALIZER TRANSFORMS
# ============================================================================

def test_severity_transformer_exhaustive():
    """Verify severity normalizer maps strings, ints, custom maps, and fallback tiers."""
    assert normalize_severity("5") == SeverityTier.CRITICAL
    assert normalize_severity("4") == SeverityTier.HIGH
    assert normalize_severity("3") == SeverityTier.MEDIUM
    assert normalize_severity("2") == SeverityTier.LOW
    assert normalize_severity("1") == SeverityTier.INFORMATIONAL
    assert normalize_severity("0") == SeverityTier.INFORMATIONAL
    assert normalize_severity("P1") == SeverityTier.CRITICAL
    assert normalize_severity("P2") == SeverityTier.HIGH
    assert normalize_severity("P3") == SeverityTier.MEDIUM
    assert normalize_severity("P4") == SeverityTier.LOW
    assert normalize_severity("CRITICAL") == SeverityTier.CRITICAL
    assert normalize_severity("Fatal") == SeverityTier.CRITICAL
    assert normalize_severity("Warning") == SeverityTier.MEDIUM
    assert normalize_severity("Notice") == SeverityTier.INFORMATIONAL

    # Custom mapping dictionary override
    custom_map = {"catastrophic": "CRITICAL", "benign": "INFORMATIONAL"}
    assert normalize_severity("catastrophic", custom_mapping=custom_map) == SeverityTier.CRITICAL
    assert normalize_severity("benign", custom_mapping=custom_map) == SeverityTier.INFORMATIONAL

    # Unknown fallback
    assert normalize_severity("unknown_x", default_fallback=SeverityTier.HIGH) == SeverityTier.HIGH


def test_field_mapping_engine_vendor_variations():
    """Verify normalizer handles multiple vendor schemas (CrowdStrike, Elastic, QRadar)."""
    # 1. CrowdStrike style alert with custom FieldMappingProfile
    profile = FieldMappingProfile(
        profile_id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        dataset_type="alert_metadata",
        version=1,
        mapping_rules={
            "event_id": "raw_ref_id",
            "EventTime_UTC": "event_timestamp",
            "TargetHost": "asset_id",
            "Signature_Name": "action",
            "RiskLevel": "severity",
            "SrcAddr": "source_ip",
            "DstAddr": "destination_ip",
            "assigned_analyst_id": "user_id",
        },
        transform_rules={
            "severity": {"mapping_dictionary": {"Critical": "CRITICAL"}},
        },
        is_active=True,
    )
    cs_row = {
        "event_id": "CS-99128",
        "EventTime_UTC": "2026-08-25T14:22:10Z",
        "TargetHost": "WORKSTATION-42",
        "Signature_Name": "Falcon Sensor Malicious Activity",
        "RiskLevel": "Critical",
        "SrcAddr": "10.0.1.5",
        "DstAddr": "198.51.100.1",
        "assigned_analyst_id": "SOC-OP-01",
    }
    engine = FieldMappingEngine(DatasetType.ALERT_METADATA, mapping_profile=profile)
    norm = engine.normalize_record(cs_row, row_index=1)

    assert norm["raw_ref_id"] == "CS-99128"
    assert norm["asset_id"] == "WORKSTATION-42"
    assert norm["action"] == "Falcon Sensor Malicious Activity"
    assert norm["severity"] == "CRITICAL"
    assert norm["source_ip"] == "10.0.1.5"
    assert norm["destination_ip"] == "198.51.100.1"
    assert norm["user_id"] == "SOC-OP-01"
    assert norm["normalized_payload"]["_row_index"] == 1


def test_field_mapping_engine_custom_date_format():
    """Verify mapping profile custom date format is correctly parsed."""
    profile = FieldMappingProfile(
        profile_id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        dataset_type="case_management",
        version=1,
        mapping_rules={"ticket": "raw_ref_id", "opened": "event_timestamp"},
        transform_rules={"timestamp": {"format": "%d-%b-%Y %H:%M:%S"}},
        is_active=True,
    )
    engine = FieldMappingEngine(DatasetType.CASE_MANAGEMENT, mapping_profile=profile)
    raw = {"ticket": "TCK-881", "opened": "25-Aug-2026 16:45:00", "title": "Security Finding"}
    norm = engine.normalize_record(raw, row_index=5)

    assert norm["raw_ref_id"] == "TCK-881"
    assert norm["event_timestamp"].day == 25
    assert norm["event_timestamp"].month == 8
    assert norm["event_timestamp"].year == 2026
    assert norm["event_timestamp"].hour == 16


# ============================================================================
# 5. END-TO-END PIPELINE LIFECYCLE & STATE TRANSITIONS
# ============================================================================

def test_pipeline_all_quarantined_returns_failed_status(sync_db: Session, sample_entity: Entity):
    """Verify submission where all rows fail validation returns FAILED status."""
    sub_id = uuid.uuid4()
    sub = RawSubmission(
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="all_bad.csv",
        file_size_bytes=512,
        mime_type="text/csv",
        minio_raw_path="raw/bad.csv",
        sha256_hash="bad_hash",
        ingestion_status="PENDING",
    )
    sync_db.add(sub)
    sync_db.commit()

    all_bad_csv = (
        "alert_id,timestamp\n"
        ",INVALID_1\n"
        ",INVALID_2\n"
    )
    result = IngestionPipelineService.process_sync(
        db=sync_db,
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type=DatasetType.ALERT_METADATA,
        raw_content=all_bad_csv,
    )

    assert result.status == SubmissionStatus.FAILED
    assert result.total_rows == 2
    assert result.valid_rows == 0
    assert result.quarantined_rows == 2

    # Verify DB update
    updated_sub = sync_db.get(RawSubmission, sub_id)
    assert updated_sub.ingestion_status == SubmissionStatus.FAILED.value
    assert updated_sub.quarantined_row_count == 2
    assert updated_sub.valid_row_count == 0


def test_pipeline_zero_rows_returns_failed_status(sync_db: Session, sample_entity: Entity):
    """Verify submission with header-only or empty content returns FAILED status."""
    sub_id = uuid.uuid4()
    sub = RawSubmission(
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="empty.csv",
        file_size_bytes=30,
        mime_type="text/csv",
        minio_raw_path="raw/empty.csv",
        sha256_hash="empty_hash",
        ingestion_status="PENDING",
    )
    sync_db.add(sub)
    sync_db.commit()

    header_only_csv = "alert_id,timestamp,severity\n"
    result = IngestionPipelineService.process_sync(
        db=sync_db,
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type=DatasetType.ALERT_METADATA,
        raw_content=header_only_csv,
    )

    assert result.status == SubmissionStatus.FAILED
    assert result.total_rows == 0
    assert result.valid_rows == 0
    assert result.quarantined_rows == 0
