"""Default field resolution mappings and standard event type associations."""

from typing import Dict, List, Optional, Union
from shared.events.enums import DatasetType, StandardEventType


DATASET_TO_EVENT_TYPE: Dict[DatasetType, StandardEventType] = {
    DatasetType.ALERT_METADATA: StandardEventType.ALERT,
    DatasetType.CASE_MANAGEMENT: StandardEventType.CASE,
    DatasetType.INVESTIGATION_RECORDS: StandardEventType.INVESTIGATION,
    DatasetType.ESCALATION_RECORDS: StandardEventType.ESCALATION,
    DatasetType.ASSET_INVENTORY: StandardEventType.ASSET,
    DatasetType.INCIDENT_REPORTS: StandardEventType.INCIDENT,
    DatasetType.COVERAGE_REPORTS: StandardEventType.COVERAGE,
    DatasetType.ANALYST_ACTIVITY: StandardEventType.ACTIVITY,
}

DATASET_PRIMARY_KEYS: Dict[DatasetType, List[str]] = {
    DatasetType.ALERT_METADATA: ["alert_id", "Incident_ID", "alertId", "alert_uid", "id"],
    DatasetType.CASE_MANAGEMENT: ["case_id", "ticket_id", "caseId", "case_number", "id"],
    DatasetType.INVESTIGATION_RECORDS: ["investigation_id", "inv_id", "investigationId", "id"],
    DatasetType.ESCALATION_RECORDS: ["escalation_id", "esc_id", "escalationId", "id"],
    DatasetType.ASSET_INVENTORY: ["asset_id", "assetId", "device_id", "id"],
    DatasetType.INCIDENT_REPORTS: ["incident_id", "incidentId", "report_id", "id"],
    DatasetType.COVERAGE_REPORTS: ["coverage_id", "coverageId", "report_id", "id"],
    DatasetType.ANALYST_ACTIVITY: ["activity_id", "activityId", "log_id", "id"],
}

# Alias candidate priority lists for canonical fields
CANONICAL_FIELD_ALIASES: Dict[str, List[str]] = {
    "raw_ref_id": [
        "alert_id", "case_id", "investigation_id", "escalation_id",
        "asset_id", "incident_id", "coverage_id", "activity_id",
        "id", "Incident_ID", "ticket_id", "alertId", "caseId", "inv_id", "esc_id", "report_id"
    ],
    "event_timestamp": [
        "timestamp", "event_timestamp", "event_time", "EventTime_UTC",
        "created_at", "declared_at", "reported_at", "escalated_at",
        "opened_at", "time", "@timestamp", "activity_time"
    ],
    "asset_id": [
        "asset_id", "hostname", "TargetHost", "device_id", "target_asset",
        "affected_asset", "affected_assets", "host", "server_name"
    ],
    "user_id": [
        "analyst_id", "user_id", "assigned_analyst", "assigned_analyst_id",
        "escalated_by", "escalated_from", "operator_id", "owner", "owner_email"
    ],
    "action": [
        "action", "rule_name", "Signature_Name", "alert_name", "investigation_action",
        "activity_type", "title", "tool_name", "action_taken"
    ],
    "status": [
        "status", "State", "approval_status", "resolution", "resolution_code", "state"
    ],
    "severity": [
        "severity", "RiskLevel", "priority", "criticality", "criticality_tier", "level"
    ],
    "source_ip": [
        "source_ip", "src_ip", "SrcAddr", "src_addr", "sourceIp", "client_ip"
    ],
    "destination_ip": [
        "destination_ip", "dest_ip", "dst_ip", "DstAddr", "dst_addr", "destinationIp", "target_ip"
    ],
}


def get_standard_event_type(dataset_type: Union[DatasetType, str]) -> StandardEventType:
    """Resolves DatasetType to its canonical StandardEventType."""
    if isinstance(dataset_type, str):
        try:
            dataset_type = DatasetType(dataset_type)
        except ValueError:
            return StandardEventType.ALERT
    return DATASET_TO_EVENT_TYPE.get(dataset_type, StandardEventType.ALERT)
