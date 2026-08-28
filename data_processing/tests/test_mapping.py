"""Tests for field mapping engine and canonical event normalizer."""

import uuid
import pytest

from shared.events.enums import DatasetType, SeverityTier, StandardEventType
from shared.models.mapping import FieldMappingProfile
from app.mapping.defaults import get_standard_event_type
from app.mapping.engine import FieldMappingEngine
from app.mapping.normalizer import CanonicalNormalizer


def test_standard_event_type_associations():
    """Verifies that each dataset type maps to the correct standard event type."""
    assert get_standard_event_type(DatasetType.ALERT_METADATA) == StandardEventType.ALERT
    assert get_standard_event_type(DatasetType.CASE_MANAGEMENT) == StandardEventType.CASE
    assert get_standard_event_type(DatasetType.INVESTIGATION_RECORDS) == StandardEventType.INVESTIGATION
    assert get_standard_event_type(DatasetType.ESCALATION_RECORDS) == StandardEventType.ESCALATION
    assert get_standard_event_type(DatasetType.ASSET_INVENTORY) == StandardEventType.ASSET
    assert get_standard_event_type(DatasetType.INCIDENT_REPORTS) == StandardEventType.INCIDENT
    assert get_standard_event_type(DatasetType.COVERAGE_REPORTS) == StandardEventType.COVERAGE
    assert get_standard_event_type(DatasetType.ANALYST_ACTIVITY) == StandardEventType.ACTIVITY


def test_field_mapping_engine_default_alias_resolution():
    """Tests normalizer resolving canonical attributes without explicit mapping profile."""
    engine = FieldMappingEngine(DatasetType.ALERT_METADATA)
    raw_row = {
        "alert_id": "ALT-007",
        "timestamp": "2026-08-25T15:00:00Z",
        "rule_name": "Suspicious PowerShell Execution",
        "severity": "CRITICAL",
        "source_ip": "192.168.1.50",
        "destination_ip": "10.0.0.1",
        "asset_id": "SRV-FINANCE-01",
        "status": "OPEN",
    }
    norm = engine.normalize_record(raw_row, row_index=1)

    assert norm["raw_ref_id"] == "ALT-007"
    assert norm["standard_event_type"] == StandardEventType.ALERT.value
    assert norm["severity"] == "CRITICAL"
    assert norm["action"] == "Suspicious PowerShell Execution"
    assert norm["asset_id"] == "SRV-FINANCE-01"
    assert norm["source_ip"] == "192.168.1.50"
    assert norm["raw_row_index"] == 1
    assert "alert_id" in norm["normalized_payload"]


def test_field_mapping_engine_custom_profile():
    """Tests normalizer applying custom FieldMappingProfile (Splunk/QRadar vendor schema)."""
    entity_id = uuid.uuid4()
    profile = FieldMappingProfile(
        profile_id=uuid.uuid4(),
        entity_id=entity_id,
        dataset_type="alert_metadata",
        version=1,
        mapping_rules={
            "Incident_ID": "raw_ref_id",
            "EventTime_UTC": "event_timestamp",
            "TargetHost": "asset_id",
            "Signature_Name": "action",
            "RiskLevel": "severity",
            "SrcAddr": "source_ip",
            "DstAddr": "destination_ip",
            "State": "status",
        },
        transform_rules={
            "timestamp": {"format": "%Y-%m-%d %H:%M:%S"},
            "severity": {
                "mapping_dictionary": {"5": "CRITICAL", "4": "HIGH", "3": "MEDIUM"},
                "default_fallback": "MEDIUM",
            },
            "defaults": {"vendor": "Splunk-ES"},
        },
        is_active=True,
    )

    engine = FieldMappingEngine(DatasetType.ALERT_METADATA, mapping_profile=profile)
    raw_vendor_row = {
        "Incident_ID": "SPLK-9901",
        "EventTime_UTC": "2026-08-25 18:30:00",
        "TargetHost": "domain-ctrl-01",
        "Signature_Name": "Mimikatz LSASS Dump",
        "RiskLevel": "5",
        "SrcAddr": "172.16.0.4",
        "DstAddr": "172.16.0.1",
        "State": "new",
    }

    norm = engine.normalize_record(raw_vendor_row, row_index=42)

    assert norm["raw_ref_id"] == "SPLK-9901"
    assert norm["asset_id"] == "domain-ctrl-01"
    assert norm["action"] == "Mimikatz LSASS Dump"
    assert norm["severity"] == "CRITICAL"
    assert norm["source_ip"] == "172.16.0.4"
    assert norm["destination_ip"] == "172.16.0.1"
    assert norm["status"] == "NEW"
    assert norm["event_timestamp"].hour == 18
    assert norm["normalized_payload"]["vendor"] == "Splunk-ES"


def test_canonical_normalizer_model_generation():
    """Tests CanonicalNormalizer creating NormalizedEvent SQLAlchemy models."""
    sub_id = uuid.uuid4()
    ent_id = uuid.uuid4()
    normalizer = CanonicalNormalizer(
        submission_id=sub_id,
        entity_id=ent_id,
        dataset_type=DatasetType.INVESTIGATION_RECORDS,
    )

    raw_data = {
        "investigation_id": "INV-1001",
        "case_id": "CASE-500",
        "analyst_id": "AN-Alice",
        "timestamp": "2026-08-25T11:00:00Z",
        "action_taken": "Containment",
        "notes": "Isolated endpoint from network",
        "time_spent_minutes": 35,
    }

    event = normalizer.normalize_row(raw_data, row_index=1)

    assert event.submission_id == sub_id
    assert event.entity_id == ent_id
    assert event.dataset_type == "investigation_records"
    assert event.standard_event_type == "INVESTIGATION"
    assert event.raw_ref_id == "INV-1001"
    assert event.user_id == "AN-Alice"
    assert event.action == "Containment"
    assert normalizer.total_normalized == 1
