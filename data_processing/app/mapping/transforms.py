"""Data normalization transformers for timestamps, severity tiers, statuses, and types."""

import datetime
import re
from typing import Any, Dict, Optional, Union
from shared.events.enums import SeverityTier


SEVERITY_MAPPING_DICTIONARY: Dict[str, SeverityTier] = {
    # Numerical 1-5 (where 5 is critical or 1 is critical)
    "5": SeverityTier.CRITICAL,
    "4": SeverityTier.HIGH,
    "3": SeverityTier.MEDIUM,
    "2": SeverityTier.LOW,
    "1": SeverityTier.INFORMATIONAL,
    "0": SeverityTier.INFORMATIONAL,
    # Priority codes P1-P5
    "p1": SeverityTier.CRITICAL,
    "p1_critical": SeverityTier.CRITICAL,
    "p2": SeverityTier.HIGH,
    "p2_high": SeverityTier.HIGH,
    "p3": SeverityTier.MEDIUM,
    "p3_medium": SeverityTier.MEDIUM,
    "p4": SeverityTier.LOW,
    "p4_low": SeverityTier.LOW,
    "p5": SeverityTier.INFORMATIONAL,
    # Textual names
    "critical": SeverityTier.CRITICAL,
    "crit": SeverityTier.CRITICAL,
    "fatal": SeverityTier.CRITICAL,
    "high": SeverityTier.HIGH,
    "major": SeverityTier.HIGH,
    "medium": SeverityTier.MEDIUM,
    "med": SeverityTier.MEDIUM,
    "moderate": SeverityTier.MEDIUM,
    "warning": SeverityTier.MEDIUM,
    "warn": SeverityTier.MEDIUM,
    "low": SeverityTier.LOW,
    "minor": SeverityTier.LOW,
    "info": SeverityTier.INFORMATIONAL,
    "informational": SeverityTier.INFORMATIONAL,
    "notice": SeverityTier.INFORMATIONAL,
    "debug": SeverityTier.INFORMATIONAL,
}


def parse_timestamp(
    val: Any,
    date_format: Optional[str] = None,
    tz_name: str = "UTC",
) -> Optional[datetime.datetime]:
    """Parses raw timestamp value into a timezone-aware UTC datetime."""
    if val is None:
        return None

    if isinstance(val, datetime.datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=datetime.timezone.utc)
        return val.astimezone(datetime.timezone.utc)

    if isinstance(val, datetime.date):
        return datetime.datetime.combine(val, datetime.time.min, tzinfo=datetime.timezone.utc)

    if isinstance(val, (int, float)):
        try:
            if val > 1e11:  # Epoch milliseconds
                return datetime.datetime.fromtimestamp(val / 1000.0, tz=datetime.timezone.utc)
            return datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
        except Exception:
            return None

    val_str = str(val).strip()
    if not val_str:
        return None

    if val_str.isdigit():
        num_val = int(val_str)
        if num_val > 1e11:
            return datetime.datetime.fromtimestamp(num_val / 1000.0, tz=datetime.timezone.utc)
        return datetime.datetime.fromtimestamp(num_val, tz=datetime.timezone.utc)

    # Custom format if specified
    if date_format and date_format.upper() not in ("ISO8601", "AUTO"):
        try:
            dt = datetime.datetime.strptime(val_str, date_format)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            pass

    # ISO8601 parsing
    try:
        clean_iso = val_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        pass

    # Fallback formats
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
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(val_str, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(datetime.timezone.utc)
        except ValueError:
            continue

    return None


def normalize_severity(
    val: Any,
    custom_mapping: Optional[Dict[str, str]] = None,
    default_fallback: SeverityTier = SeverityTier.MEDIUM,
) -> SeverityTier:
    """Normalizes raw severity value to SeverityTier enum."""
    if val is None:
        return default_fallback

    if isinstance(val, SeverityTier):
        return val

    key = str(val).strip().lower()
    
    # 1. Custom mapping dictionary if provided
    if custom_mapping:
        lower_custom = {k.lower(): v for k, v in custom_mapping.items()}
        if key in lower_custom:
            target_str = lower_custom[key].upper()
            try:
                return SeverityTier(target_str)
            except ValueError:
                pass

    # 2. Standard severity dictionary
    if key in SEVERITY_MAPPING_DICTIONARY:
        return SEVERITY_MAPPING_DICTIONARY[key]

    # 3. Direct enum match attempt
    try:
        return SeverityTier(str(val).strip().upper())
    except ValueError:
        return default_fallback


def normalize_status(val: Any, default_status: str = "OPEN") -> str:
    """Normalizes status string."""
    if val is None:
        return default_status
    cleaned = str(val).strip().upper()
    return cleaned if cleaned else default_status


def cast_boolean(val: Any) -> bool:
    """Robust boolean caster."""
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    str_val = str(val).strip().lower()
    return str_val in ("true", "1", "t", "yes", "y", "enabled")
