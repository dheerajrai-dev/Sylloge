"""Tests for row-level quarantine engine and validation failure diagnoses."""

import uuid
import pytest
from unittest.mock import MagicMock, patch

from shared.events.enums import DatasetType
from app.parsers.base import ParsedRow
from app.quarantine.errors import QuarantineErrorCode, RowValidationFailure
from app.quarantine.validator import RowValidator
from app.quarantine.manager import QuarantineManager


def test_row_validator_missing_required_field():
    """Validates missing alert_id or timestamp generates MISSING_REQUIRED_FIELD error."""
    validator = RowValidator(DatasetType.ALERT_METADATA)

    # Missing alert_id
    row1 = ParsedRow(row_index=1, data={"timestamp": "2026-08-25T10:00:00Z", "severity": "HIGH"})
    fail1 = validator.validate_parsed_row(row1)
    assert fail1 is not None
    assert fail1.error_code == QuarantineErrorCode.MISSING_REQUIRED_FIELD
    assert "alert_id" in fail1.failed_fields

    # Missing timestamp
    row2 = ParsedRow(row_index=2, data={"alert_id": "ALT-100", "severity": "HIGH"})
    fail2 = validator.validate_parsed_row(row2)
    assert fail2 is not None
    assert fail2.error_code == QuarantineErrorCode.MISSING_REQUIRED_FIELD
    assert "timestamp" in fail2.failed_fields


def test_row_validator_datetime_parse_error():
    """Validates unparseable timestamps generate DATETIME_PARSE_ERROR."""
    validator = RowValidator(DatasetType.ALERT_METADATA)
    row = ParsedRow(
        row_index=1,
        data={"alert_id": "ALT-101", "timestamp": "NOT_A_VALID_DATE_STRING", "severity": "LOW"},
    )
    fail = validator.validate_parsed_row(row)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.DATETIME_PARSE_ERROR
    assert "timestamp" in fail.failed_fields


def test_row_validator_type_mismatch():
    """Validates non-numeric value in numeric fields generates TYPE_MISMATCH."""
    validator = RowValidator(DatasetType.COVERAGE_REPORTS)
    row = ParsedRow(
        row_index=1,
        data={
            "coverage_id": "COV-01",
            "reported_at": "2026-08-25T10:00:00Z",
            "uptime_pct": "not_a_number_pct",
        },
    )
    fail = validator.validate_parsed_row(row)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.TYPE_MISMATCH
    assert "uptime_pct" in fail.failed_fields


def test_row_validator_duplicate_primary_key():
    """Validates duplicate primary key in same batch generates DUPLICATE_PRIMARY_KEY."""
    validator = RowValidator(DatasetType.CASE_MANAGEMENT)

    row1 = ParsedRow(
        row_index=1,
        data={"case_id": "CASE-DUPE-01", "created_at": "2026-08-25T10:00:00Z"},
    )
    assert validator.validate_parsed_row(row1) is None

    row2 = ParsedRow(
        row_index=2,
        data={"case_id": "CASE-DUPE-01", "created_at": "2026-08-25T10:05:00Z"},
    )
    fail = validator.validate_parsed_row(row2)
    assert fail is not None
    assert fail.error_code == QuarantineErrorCode.DUPLICATE_PRIMARY_KEY


def test_quarantine_manager_summary_and_dump():
    """Tests quarantine manager accumulation, summary generation, and JSON dump output."""
    sub_id = uuid.uuid4()
    ent_id = uuid.uuid4()
    mgr = QuarantineManager(submission_id=sub_id, entity_id=ent_id, dataset_type=DatasetType.ALERT_METADATA)

    f1 = RowValidationFailure(
        error_code=QuarantineErrorCode.MISSING_REQUIRED_FIELD,
        message="Missing alert_id",
        failed_fields=["alert_id"],
        raw_data={"timestamp": "2026-08-25T10:00:00Z"},
        row_index=1,
    )
    f2 = RowValidationFailure(
        error_code=QuarantineErrorCode.DATETIME_PARSE_ERROR,
        message="Invalid timestamp",
        failed_fields=["timestamp"],
        raw_data={"alert_id": "ALT-2", "timestamp": "invalid"},
        row_index=2,
    )

    mgr.record_failure(f1)
    mgr.record_failure(f2)

    assert mgr.total_quarantined == 2

    # Summary
    summary = mgr.get_summary()
    assert summary.total_quarantined == 2
    assert summary.failure_reasons_breakdown[QuarantineErrorCode.MISSING_REQUIRED_FIELD.value] == 1
    assert summary.failure_reasons_breakdown[QuarantineErrorCode.DATETIME_PARSE_ERROR.value] == 1
    assert summary.failed_fields_breakdown["alert_id"] == 1
    assert summary.failed_fields_breakdown["timestamp"] == 1

    # Dump payload
    dump = mgr.export_dump_payload()
    assert dump["total_quarantined"] == 2
    assert len(dump["rows"]) == 2
    assert dump["rows"][0]["row_index"] == 1
    assert dump["rows"][1]["row_index"] == 2


def test_quarantine_manager_minio_upload_mocked():
    """Verifies that MinIO upload interacts with minio_client."""
    sub_id = uuid.uuid4()
    ent_id = uuid.uuid4()
    mgr = QuarantineManager(submission_id=sub_id, entity_id=ent_id, dataset_type=DatasetType.ALERT_METADATA)

    f = RowValidationFailure(
        error_code=QuarantineErrorCode.CORRUPTED_ROW,
        message="CSV column mismatch",
        failed_fields=["__raw__"],
        raw_data={"col1": "val1"},
        row_index=1,
    )
    mgr.record_failure(f)

    with patch("app.quarantine.manager.minio_client.upload_json", return_value="fake_sha256") as mock_upload:
        obj_name = mgr.save_dump_to_minio()
        assert obj_name == f"quarantines/{ent_id}/{sub_id}_quarantined.json"
        mock_upload.assert_called_once()
