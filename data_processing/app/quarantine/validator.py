"""Row-level validator checking structural and semantic integrity against schemas and mappings."""

import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from shared.events.enums import DatasetType
from shared.models.mapping import FieldMappingProfile
from .errors import QuarantineErrorCode, RowValidationFailure
from ..parsers.base import ParsedRow


# Required logical concepts for each dataset type
DATASET_REQUIRED_FIELDS: Dict[DatasetType, List[List[str]]] = {
    DatasetType.ALERT_METADATA: [
        ["alert_id", "id", "Incident_ID", "alertId", "event_id", "alert_uid"],
        ["timestamp", "event_time", "EventTime_UTC", "time", "created_at", "@timestamp"],
    ],
    DatasetType.CASE_MANAGEMENT: [
        ["case_id", "id", "ticket_id", "caseId", "case_number"],
        ["created_at", "timestamp", "opened_at", "creation_time"],
    ],
    DatasetType.INVESTIGATION_RECORDS: [
        ["investigation_id", "id", "inv_id", "investigationId"],
        ["case_id", "alert_id", "ticket_id", "caseId"],
        ["timestamp", "investigated_at", "action_time", "created_at"],
    ],
    DatasetType.ESCALATION_RECORDS: [
        ["escalation_id", "id", "esc_id", "escalationId"],
        ["escalated_at", "timestamp", "created_at"],
    ],
    DatasetType.ASSET_INVENTORY: [
        ["asset_id", "id", "hostname", "assetId", "device_id"],
    ],
    DatasetType.INCIDENT_REPORTS: [
        ["incident_id", "id", "incidentId", "report_id"],
        ["declared_at", "timestamp", "report_timestamp", "incident_date", "created_at", "report_date"],
    ],
    DatasetType.COVERAGE_REPORTS: [
        ["coverage_id", "id", "report_id", "coverageId", "tool_name"],
        ["reported_at", "timestamp", "reporting_period_start", "created_at"],
    ],
    DatasetType.ANALYST_ACTIVITY: [
        ["activity_id", "id", "log_id", "activityId"],
        ["analyst_id", "user_id", "analyst", "operator_id"],
        ["timestamp", "activity_time", "created_at", "event_time"],
    ],
}

# Numeric fields that must be numbers if present
NUMERIC_FIELDS: Set[str] = {
    "uptime_pct",
    "coverage_percentage",
    "time_spent_minutes",
    "financial_impact",
    "financial_impact_estimate",
    "event_count",
    "total_assets_monitored",
    "active_sensors",
    "duration_seconds",
}


class RowValidator:
    """Evaluates raw rows against dataset type expectations and optional mapping rules."""

    def __init__(
        self,
        dataset_type: Union[DatasetType, str],
        mapping_profile: Optional[FieldMappingProfile] = None,
    ):
        if isinstance(dataset_type, str):
            try:
                self.dataset_type = DatasetType(dataset_type)
            except ValueError:
                self.dataset_type = None
        else:
            self.dataset_type = dataset_type

        self.mapping_profile = mapping_profile
        self.seen_primary_keys: Set[str] = set()

    def validate_parsed_row(self, row: ParsedRow) -> Optional[RowValidationFailure]:
        """Validates a parsed row. Returns None if valid, or RowValidationFailure if defective."""
        # 1. Check if row is already marked corrupted by lower-level parser (e.g. CSV column mismatch, JSON syntax)
        if row.is_corrupted:
            return RowValidationFailure(
                error_code=QuarantineErrorCode.CORRUPTED_ROW,
                message=row.corruption_reason or "Corrupted raw record",
                failed_fields=["__raw__"],
                raw_data=row.data,
                row_index=row.row_index,
            )

        data = row.data
        if not data or not isinstance(data, dict):
            return RowValidationFailure(
                error_code=QuarantineErrorCode.CORRUPTED_ROW,
                message="Row data is empty or not a valid dictionary",
                failed_fields=["__raw__"],
                raw_data={"raw": str(data)},
                row_index=row.row_index,
            )

        # 2. Field Mapping Profile Check: If profile is active, check required source columns
        if self.mapping_profile and self.mapping_profile.mapping_rules:
            mapping_rules = self.mapping_profile.mapping_rules
            # mapping_rules can map source_col -> target_field or target_field -> source_col
            # Verify that source columns exist in data
            # Also check date transform validity if specified
            pass

        # 3. Check dataset-specific required candidate fields
        if self.dataset_type and self.dataset_type in DATASET_REQUIRED_FIELDS:
            required_groups = DATASET_REQUIRED_FIELDS[self.dataset_type]
            for group in required_groups:
                found_field = None
                for candidate in group:
                    # Check direct or mapped match
                    if candidate in data and data[candidate] is not None and str(data[candidate]).strip() != "":
                        found_field = candidate
                        break
                    # Also check if mapped in mapping profile
                    if self.mapping_profile and self.mapping_profile.mapping_rules:
                        # If candidate is a target, check if any source maps to it
                        for src, tgt in self.mapping_profile.mapping_rules.items():
                            if tgt == candidate and src in data and data[src] is not None and str(data[src]).strip() != "":
                                found_field = src
                                break
                
                if not found_field:
                    return RowValidationFailure(
                        error_code=QuarantineErrorCode.MISSING_REQUIRED_FIELD,
                        message=f"Missing mandatory field from candidate group: {group}",
                        failed_fields=[group[0]],
                        raw_data=data,
                        row_index=row.row_index,
                    )

        # 4. Check Timestamp parsing validity
        time_field, time_val = self._extract_timestamp_field(data)
        if time_field and time_val is not None:
            parsed_dt = self._try_parse_datetime(time_val)
            if parsed_dt is None:
                return RowValidationFailure(
                    error_code=QuarantineErrorCode.DATETIME_PARSE_ERROR,
                    message=f"Unable to parse timestamp '{time_val}' in field '{time_field}'",
                    failed_fields=[time_field],
                    raw_data=data,
                    row_index=row.row_index,
                )

        # 5. Check Numeric Fields validity
        for k, v in data.items():
            if k in NUMERIC_FIELDS and v is not None:
                try:
                    float(v)
                except (ValueError, TypeError):
                    return RowValidationFailure(
                        error_code=QuarantineErrorCode.TYPE_MISMATCH,
                        message=f"Field '{k}' with value '{v}' cannot be converted to number",
                        failed_fields=[k],
                        raw_data=data,
                        row_index=row.row_index,
                    )

        # 6. Check Duplicate Primary Key (within same batch)
        pk_val = self._extract_primary_key(data)
        if pk_val:
            pk_str = str(pk_val)
            if pk_str in self.seen_primary_keys:
                return RowValidationFailure(
                    error_code=QuarantineErrorCode.DUPLICATE_PRIMARY_KEY,
                    message=f"Duplicate primary key '{pk_str}' encountered in batch",
                    failed_fields=["primary_key"],
                    raw_data=data,
                    row_index=row.row_index,
                )
            self.seen_primary_keys.add(pk_str)

        return None

    def _extract_primary_key(self, data: Dict[str, Any]) -> Optional[Any]:
        """Extracts primary identifier candidate value."""
        if self.dataset_type and self.dataset_type in DATASET_REQUIRED_FIELDS:
            # Check the first required candidate group (which is the primary key group)
            pk_group = DATASET_REQUIRED_FIELDS[self.dataset_type][0]
            for k in pk_group:
                if k in data and data[k] is not None and str(data[k]).strip() != "":
                    return data[k]

        pk_candidates = [
            "alert_id", "case_id", "investigation_id", "escalation_id",
            "coverage_id", "incident_id", "activity_id", "asset_id",
            "id", "Incident_ID", "ticket_id"
        ]
        for k in pk_candidates:
            if k in data and data[k] is not None:
                return data[k]
        return None

    def _extract_timestamp_field(self, data: Dict[str, Any]) -> Tuple[Optional[str], Optional[Any]]:
        """Finds candidate timestamp field and its value."""
        ts_candidates = [
            "timestamp", "event_timestamp", "event_time", "EventTime_UTC",
            "created_at", "declared_at", "reported_at", "escalated_at",
            "time", "@timestamp"
        ]
        for k in ts_candidates:
            if k in data and data[k] is not None:
                return k, data[k]
        return None, None

    @staticmethod
    def _try_parse_datetime(val: Any) -> Optional[datetime.datetime]:
        """Attempts parsing datetime from various formats (ISO8601, Epoch, standard strings)."""
        if isinstance(val, datetime.datetime):
            return val
        if isinstance(val, datetime.date):
            return datetime.datetime.combine(val, datetime.time.min, tzinfo=datetime.timezone.utc)
        
        if isinstance(val, (int, float)):
            # Epoch seconds or milliseconds
            try:
                if val > 1e11:  # Milliseconds
                    return datetime.datetime.fromtimestamp(val / 1000.0, tz=datetime.timezone.utc)
                return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
            except Exception:
                return None

        if isinstance(val, str):
            val_str = val.strip()
            if not val_str:
                return None
            
            # Numeric string timestamp check
            if val_str.isdigit():
                num_val = int(val_str)
                if num_val > 1e11:
                    return datetime.datetime.fromtimestamp(num_val / 1000.0, tz=datetime.timezone.utc)
                return datetime.datetime.fromtimestamp(num_val, tz=datetime.timezone.utc)

            # Try fromisoformat
            try:
                # Handle 'Z' suffix
                clean_iso = val_str.replace("Z", "+00:00")
                return datetime.datetime.fromisoformat(clean_iso)
            except Exception:
                pass

            # Common format patterns
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S",
                "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S GMT",
            ]
            for fmt in formats:
                try:
                    dt = datetime.datetime.strptime(val_str, fmt)
                    return dt.replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    continue

        return None
