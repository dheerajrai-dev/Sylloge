"""Tests for streaming CSV and JSON parsers across all 8 dataset types."""

import io
import json
import pytest

from shared.events.enums import DatasetType
from data_processing.parsers import (
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


def test_csv_parser_standard_and_delimiters():
    """Verifies CSV parser correctly identifies and parses comma, tab, semicolon, and pipe delimiters."""
    # Comma
    csv_data = "alert_id,timestamp,severity\nALT-001,2026-08-25T10:00:00Z,CRITICAL\nALT-002,2026-08-25T10:05:00Z,HIGH"
    parser = CSVParser()
    rows = list(parser.parse_stream(csv_data))
    assert len(rows) == 2
    assert rows[0].row_index == 1
    assert rows[0].data["alert_id"] == "ALT-001"
    assert rows[0].data["severity"] == "CRITICAL"
    assert not rows[0].is_corrupted

    # Semicolon
    csv_semi = "case_id;title;status\nCASE-101;Ransomware Alert;OPEN\nCASE-102;Phishing;CLOSED"
    rows_semi = list(CSVParser().parse_stream(csv_semi))
    assert len(rows_semi) == 2
    assert rows_semi[0].data["case_id"] == "CASE-101"
    assert rows_semi[0].data["status"] == "OPEN"

    # Tab (TSV)
    tsv_data = "asset_id\thostname\tcriticality\nAST-01\tsrv-db-01\tHIGH"
    rows_tsv = list(CSVParser().parse_stream(tsv_data))
    assert len(rows_tsv) == 1
    assert rows_tsv[0].data["hostname"] == "srv-db-01"

    # Pipe (PSV)
    psv_data = "incident_id|severity|declared_at\nINC-1|CRITICAL|2026-08-20T12:00:00Z"
    rows_psv = list(CSVParser().parse_stream(psv_data))
    assert len(rows_psv) == 1
    assert rows_psv[0].data["incident_id"] == "INC-1"


def test_csv_parser_bom_and_null_normalization():
    """Tests UTF-8 BOM stripping and null string normalization."""
    raw_with_bom = "\ufeffalert_id,rule_name,source_ip,destination_ip\nALT-999,BruteForce,10.0.0.1,null\nALT-998,PortScan,N/A,None"
    rows = list(CSVParser().parse_stream(raw_with_bom))
    assert len(rows) == 2
    assert "alert_id" in rows[0].data  # BOM should not corrupt header name
    assert rows[0].data["destination_ip"] is None
    assert rows[1].data["source_ip"] is None
    assert rows[1].data["destination_ip"] is None


def test_csv_parser_column_mismatch_resilience():
    """Tests that mismatched column counts yield a corrupted ParsedRow without crashing."""
    malformed_csv = "alert_id,timestamp,severity\nALT-1,2026-08-25T10:00:00Z,HIGH\nALT-2,2026-08-25T10:01:00Z\nALT-3,2026-08-25T10:02:00Z,LOW,EXTRA_VALUE"
    rows = list(CSVParser().parse_stream(malformed_csv))
    assert len(rows) == 3
    assert not rows[0].is_corrupted
    assert rows[1].is_corrupted
    assert "Column count mismatch" in rows[1].corruption_reason
    assert rows[2].is_corrupted
    assert "__extra__" in rows[2].data


def test_json_parser_array_and_wrapper_layouts():
    """Tests JSON array, wrapped objects, and single object parsing."""
    # 1. Top-level array
    json_arr = json.dumps([
        {"alert_id": "ALT-1", "severity": "HIGH"},
        {"alert_id": "ALT-2", "severity": "MEDIUM"},
    ])
    rows = list(JSONParser().parse_stream(json_arr))
    assert len(rows) == 2
    assert rows[0].data["alert_id"] == "ALT-1"

    # 2. Wrapped payload in 'records'
    wrapped_json = json.dumps({
        "records": [
            {"case_id": "C-1", "title": "Phishing Incident"},
            {"case_id": "C-2", "title": "Data Leak"},
        ]
    })
    rows_wrap = list(JSONParser().parse_stream(wrapped_json))
    assert len(rows_wrap) == 2
    assert rows_wrap[0].data["case_id"] == "C-1"

    # 3. Single object
    single_json = json.dumps({"incident_id": "INC-99", "severity": "CRITICAL"})
    rows_single = list(JSONParser().parse_stream(single_json))
    assert len(rows_single) == 1
    assert rows_single[0].data["incident_id"] == "INC-99"


def test_json_parser_ndjson_and_malformed_lines():
    """Tests NDJSON / JSON Lines and recovery from malformed lines."""
    ndjson_data = (
        '{"alert_id": "ALT-10", "timestamp": "2026-08-25T01:00:00Z"}\n'
        'NOT_VALID_JSON_LINE\n'
        '{"alert_id": "ALT-11", "timestamp": "2026-08-25T02:00:00Z"}\n'
    )
    rows = list(JSONParser().parse_stream(ndjson_data))
    assert len(rows) == 3
    assert not rows[0].is_corrupted
    assert rows[0].data["alert_id"] == "ALT-10"
    assert rows[1].is_corrupted
    assert "Invalid JSON line syntax" in rows[1].corruption_reason
    assert not rows[2].is_corrupted
    assert rows[2].data["alert_id"] == "ALT-11"


@pytest.mark.parametrize("dataset_type,sample_csv,pk_key", [
    (
        DatasetType.ALERT_METADATA,
        "alert_id,timestamp,severity,rule_name\nALT-1,2026-08-25T10:00:00Z,CRITICAL,BruteForce",
        "alert_id",
    ),
    (
        DatasetType.CASE_MANAGEMENT,
        "case_id,created_at,status,priority,title\nCASE-1,2026-08-25T10:00:00Z,OPEN,P1_CRITICAL,Malware Outbreak",
        "case_id",
    ),
    (
        DatasetType.INVESTIGATION_RECORDS,
        "investigation_id,case_id,analyst_id,timestamp,action_taken,notes\nINV-1,CASE-1,AN-10,2026-08-25T11:00:00Z,Quarantine,Host quarantined",
        "investigation_id",
    ),
    (
        DatasetType.ESCALATION_RECORDS,
        "escalation_id,case_id,escalated_at,escalated_by,escalated_to,escalation_reason\nESC-1,CASE-1,2026-08-25T12:00:00Z,AN-10,TIER_2_SOC,Complex threat",
        "escalation_id",
    ),
    (
        DatasetType.ASSET_INVENTORY,
        "asset_id,hostname,ip_address,asset_type,criticality_tier\nAST-1,dc-01,10.0.0.1,DOMAIN_CONTROLLER,CROWN_JEWEL",
        "asset_id",
    ),
    (
        DatasetType.INCIDENT_REPORTS,
        "incident_id,declared_at,severity,root_cause,attack_vector\nINC-1,2026-08-25T14:00:00Z,CRITICAL,Zero Day,EXPLOIT_PUBLIC_FACING",
        "incident_id",
    ),
    (
        DatasetType.COVERAGE_REPORTS,
        "coverage_id,reporting_period_start,reported_at,tool_name,uptime_pct\nCOV-1,2026-08-01,2026-08-25T00:00:00Z,EDR,99.8",
        "coverage_id",
    ),
    (
        DatasetType.ANALYST_ACTIVITY,
        "activity_id,analyst_id,timestamp,activity_type,console_session_id\nACT-1,AN-10,2026-08-25T09:00:00Z,LOGIN,SESS-99",
        "activity_id",
    ),
])
def test_all_8_dataset_parsers_csv_and_json(dataset_type, sample_csv, pk_key):
    """Verifies that each of the 8 dataset types correctly parses both CSV and JSON."""
    parser = get_parser_for_dataset(dataset_type)

    # 1. Parse CSV
    csv_rows = list(parser.parse_stream(sample_csv))
    assert len(csv_rows) == 1
    assert not csv_rows[0].is_corrupted
    assert pk_key in csv_rows[0].data

    # 2. Parse JSON
    json_data = json.dumps([csv_rows[0].data])
    json_rows = list(parser.parse_stream(json_data))
    assert len(json_rows) == 1
    assert not json_rows[0].is_corrupted
    assert json_rows[0].data[pk_key] == csv_rows[0].data[pk_key]
