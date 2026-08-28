"""Quarantine error code classifications and error result types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class QuarantineErrorCode(str, Enum):
    """Standardized quarantine error classifications."""
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    DATETIME_PARSE_ERROR = "DATETIME_PARSE_ERROR"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    ENUM_DOMAIN_VIOLATION = "ENUM_DOMAIN_VIOLATION"
    DUPLICATE_PRIMARY_KEY = "DUPLICATE_PRIMARY_KEY"
    CORRUPTED_ROW = "CORRUPTED_ROW"
    SCHEMA_VALIDATION_ERROR = "SCHEMA_VALIDATION_ERROR"
    UNMAPPED_REQUIRED_FIELD = "UNMAPPED_REQUIRED_FIELD"


@dataclass
class RowValidationFailure:
    """Detailed diagnosis of why a raw row failed validation."""
    error_code: QuarantineErrorCode
    message: str
    failed_fields: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    row_index: int = 0
