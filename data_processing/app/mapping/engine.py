"""Field mapping profile engine for executing entity-specific normalization rules."""

import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from shared.events.enums import DatasetType, SeverityTier, StandardEventType
from shared.models.mapping import FieldMappingProfile
from .defaults import CANONICAL_FIELD_ALIASES, DATASET_PRIMARY_KEYS, get_standard_event_type
from .transforms import normalize_severity, normalize_status, parse_timestamp


class FieldMappingEngine:
    """Applies entity-specific FieldMappingProfile or fallback alias resolution to raw data records."""

    def __init__(
        self,
        dataset_type: Union[DatasetType, str],
        mapping_profile: Optional[FieldMappingProfile] = None,
    ):
        if isinstance(dataset_type, str):
            try:
                self.dataset_type = DatasetType(dataset_type)
            except ValueError:
                self.dataset_type = DatasetType.ALERT_METADATA
        else:
            self.dataset_type = dataset_type

        self.mapping_profile = mapping_profile
        self.standard_event_type = get_standard_event_type(self.dataset_type)

    def normalize_record(
        self, raw_data: Dict[str, Any], row_index: int
    ) -> Dict[str, Any]:
        """Normalizes raw dictionary record into canonical event attributes and combined payload."""
        data = dict(raw_data)
        
        # 1. Apply defaults from profile if available
        profile_transforms = self.mapping_profile.transform_rules if self.mapping_profile else {}
        profile_mapping = self.mapping_profile.mapping_rules if self.mapping_profile else {}
        
        defaults = profile_transforms.get("defaults", {}) if isinstance(profile_transforms, dict) else {}
        for k, v in defaults.items():
            if k not in data or data[k] is None:
                data[k] = v

        # 2. Resolve mapped field values
        mapped_dict = self._apply_column_mappings(data, profile_mapping)

        # 3. Extract Canonical Fields
        # Raw Ref ID
        raw_ref_id = self._extract_field(mapped_dict, data, "raw_ref_id")
        if raw_ref_id is not None:
            raw_ref_id = str(raw_ref_id)

        # Timestamp
        date_format = None
        if isinstance(profile_transforms, dict):
            ts_rule = profile_transforms.get("timestamp") or profile_transforms.get("event_timestamp") or {}
            if isinstance(ts_rule, dict):
                date_format = ts_rule.get("format")
            elif isinstance(ts_rule, str):
                date_format = ts_rule

        raw_ts_val = self._extract_field(mapped_dict, data, "event_timestamp")
        event_timestamp = parse_timestamp(raw_ts_val, date_format=date_format)
        if event_timestamp is None:
            event_timestamp = datetime.datetime.now(datetime.timezone.utc)

        # Asset ID
        asset_id = self._extract_field(mapped_dict, data, "asset_id")
        if asset_id is not None:
            if isinstance(asset_id, list):
                asset_id = ",".join(str(x) for x in asset_id)
            else:
                asset_id = str(asset_id)

        # User ID
        user_id = self._extract_field(mapped_dict, data, "user_id")
        if user_id is not None:
            user_id = str(user_id)

        # Action / Rule Name / Title
        action = self._extract_field(mapped_dict, data, "action")
        if action is not None:
            action = str(action)

        # Status
        raw_status = self._extract_field(mapped_dict, data, "status")
        status = normalize_status(raw_status) if raw_status is not None else None

        # Severity
        severity_rule = profile_transforms.get("severity") if isinstance(profile_transforms, dict) else None
        custom_sev_map = None
        default_sev = SeverityTier.MEDIUM
        if isinstance(severity_rule, dict):
            custom_sev_map = severity_rule.get("mapping_dictionary") or severity_rule.get("map")
            def_str = severity_rule.get("default_fallback") or severity_rule.get("default")
            if def_str:
                try:
                    default_sev = SeverityTier(def_str.upper())
                except ValueError:
                    pass

        raw_severity = self._extract_field(mapped_dict, data, "severity")
        severity = normalize_severity(raw_severity, custom_mapping=custom_sev_map, default_fallback=default_sev) if raw_severity is not None else None

        # IP Addresses
        source_ip = self._extract_field(mapped_dict, data, "source_ip")
        if source_ip is not None:
            source_ip = str(source_ip)

        dest_ip = self._extract_field(mapped_dict, data, "destination_ip")
        if dest_ip is not None:
            dest_ip = str(dest_ip)

        # 4. Normalized Payload (Merge all source and standard fields)
        normalized_payload = {**data, **mapped_dict}
        normalized_payload["_row_index"] = row_index
        normalized_payload["_standard_event_type"] = self.standard_event_type.value

        return {
            "dataset_type": self.dataset_type.value,
            "standard_event_type": self.standard_event_type.value,
            "event_timestamp": event_timestamp,
            "asset_id": asset_id,
            "user_id": user_id,
            "action": action,
            "status": status,
            "severity": severity.value if severity else None,
            "source_ip": source_ip,
            "destination_ip": dest_ip,
            "raw_row_index": row_index,
            "raw_ref_id": raw_ref_id,
            "normalized_payload": normalized_payload,
        }

    def _apply_column_mappings(
        self, data: Dict[str, Any], mapping_rules: Dict[str, str]
    ) -> Dict[str, Any]:
        """Applies explicit column mappings from profile."""
        mapped: Dict[str, Any] = {}
        if not mapping_rules:
            return mapped

        for k, v in mapping_rules.items():
            # Check if k is source column in data
            if k in data and data[k] is not None:
                target_field = v
                mapped[target_field] = data[k]
            # Check if v is source column in data and k is target
            elif v in data and data[v] is not None:
                target_field = k
                mapped[target_field] = data[v]

        return mapped

    def _extract_field(
        self, mapped_dict: Dict[str, Any], raw_dict: Dict[str, Any], canonical_name: str
    ) -> Optional[Any]:
        """Extracts field value from mapped dictionary or alias fallback."""
        # 1. Direct mapped dict check
        if canonical_name in mapped_dict and mapped_dict[canonical_name] is not None:
            return mapped_dict[canonical_name]

        def _clean(s: str) -> str:
            return s.lower().replace("_", "").replace(" ", "").replace("-", "")

        # 2. Check aliases in raw_dict
        if canonical_name == "raw_ref_id" and self.dataset_type in DATASET_PRIMARY_KEYS:
            specific_keys = DATASET_PRIMARY_KEYS[self.dataset_type]
            for key in specific_keys:
                if key in raw_dict and raw_dict[key] is not None:
                    return raw_dict[key]
                clean_key = _clean(key)
                for rk, rv in raw_dict.items():
                    if _clean(rk) == clean_key and rv is not None:
                        return rv

        aliases = CANONICAL_FIELD_ALIASES.get(canonical_name, [canonical_name])
        for alias in aliases:
            if alias in raw_dict and raw_dict[alias] is not None:
                return raw_dict[alias]
            clean_alias = _clean(alias)
            # Also check case-insensitive / space / underscore normalized match
            for rk, rv in raw_dict.items():
                if _clean(rk) == clean_alias and rv is not None:
                    return rv

        return None
