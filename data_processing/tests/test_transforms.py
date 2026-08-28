"""Tests for timestamp, severity, status, and boolean data transformers."""

import datetime
import pytest
from shared.events.enums import SeverityTier
from app.mapping.transforms import (
    cast_boolean,
    normalize_severity,
    normalize_status,
    parse_timestamp,
)


def test_parse_timestamp_formats():
    """Tests parsing diverse timestamp formats into UTC timezone-aware datetimes."""
    # 1. ISO 8601 UTC with Z
    dt1 = parse_timestamp("2026-08-25T14:30:00Z")
    assert dt1 is not None
    assert dt1.tzinfo == datetime.timezone.utc
    assert dt1.year == 2026 and dt1.month == 8 and dt1.day == 25
    assert dt1.hour == 14 and dt1.minute == 30

    # 2. ISO 8601 with offset (+05:30)
    dt2 = parse_timestamp("2026-08-25T20:00:00+05:30")
    assert dt2 is not None
    assert dt2.tzinfo == datetime.timezone.utc
    assert dt2.hour == 14 and dt2.minute == 30

    # 3. Standard string YYYY-MM-DD HH:MM:SS
    dt3 = parse_timestamp("2026-08-25 14:30:00")
    assert dt3 is not None
    assert dt3.year == 2026 and dt3.hour == 14

    # 4. Epoch seconds (int / float / str)
    epoch_sec = 1787668200
    dt4 = parse_timestamp(epoch_sec)
    assert dt4 is not None
    assert dt4.tzinfo == datetime.timezone.utc

    # 5. Epoch milliseconds
    epoch_ms = 1787668200000
    dt5 = parse_timestamp(epoch_ms)
    assert dt5 is not None
    assert dt5.year == dt4.year

    # 6. Custom format
    dt6 = parse_timestamp("25/08/2026 14:30", date_format="%d/%m/%Y %H:%M")
    assert dt6 is not None
    assert dt6.day == 25 and dt6.month == 8

    # 7. Invalid string returns None
    assert parse_timestamp("invalid_date") is None
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None


def test_normalize_severity_standard_and_custom():
    """Tests standard and custom severity mappings."""
    # Numeric 1-5
    assert normalize_severity("5") == SeverityTier.CRITICAL
    assert normalize_severity("4") == SeverityTier.HIGH
    assert normalize_severity("3") == SeverityTier.MEDIUM
    assert normalize_severity("2") == SeverityTier.LOW
    assert normalize_severity("1") == SeverityTier.INFORMATIONAL

    # Priority codes P1-P4
    assert normalize_severity("P1") == SeverityTier.CRITICAL
    assert normalize_severity("P2_HIGH") == SeverityTier.HIGH
    assert normalize_severity("p3") == SeverityTier.MEDIUM
    assert normalize_severity("P4_LOW") == SeverityTier.LOW

    # Textual
    assert normalize_severity("crit") == SeverityTier.CRITICAL
    assert normalize_severity("Critical") == SeverityTier.CRITICAL
    assert normalize_severity("warning") == SeverityTier.MEDIUM
    assert normalize_severity("minor") == SeverityTier.LOW
    assert normalize_severity("informational") == SeverityTier.INFORMATIONAL

    # Custom mapping override
    custom_map = {"sev_severe": "CRITICAL", "sev_moderate": "MEDIUM"}
    assert normalize_severity("sev_severe", custom_mapping=custom_map) == SeverityTier.CRITICAL
    assert normalize_severity("sev_moderate", custom_mapping=custom_map) == SeverityTier.MEDIUM

    # Unknown fallback
    assert normalize_severity("unknown_level", default_fallback=SeverityTier.LOW) == SeverityTier.LOW


def test_normalize_status_and_boolean():
    """Tests status string and boolean casting."""
    assert normalize_status("open") == "OPEN"
    assert normalize_status("in_progress") == "IN_PROGRESS"
    assert normalize_status(None, default_status="PENDING") == "PENDING"

    assert cast_boolean("True") is True
    assert cast_boolean("1") is True
    assert cast_boolean("yes") is True
    assert cast_boolean("false") is False
    assert cast_boolean("0") is False
    assert cast_boolean(None) is False
