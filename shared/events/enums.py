"""Domain enums for SAT-SA."""

from enum import Enum


class DatasetType(str, Enum):
    """The 8 supported telemetry and supervisory dataset types."""
    ALERT_METADATA = "alert_metadata"
    CASE_MANAGEMENT = "case_management"
    INVESTIGATION_RECORDS = "investigation_records"
    ESCALATION_RECORDS = "escalation_records"
    ASSET_INVENTORY = "asset_inventory"
    INCIDENT_REPORTS = "incident_reports"
    COVERAGE_REPORTS = "coverage_reports"
    ANALYST_ACTIVITY = "analyst_activity"


class SeverityTier(str, Enum):
    """Normalized finding and event severity tiers."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class StandardEventType(str, Enum):
    """Canonical event categories."""
    ALERT = "ALERT"
    CASE = "CASE"
    INVESTIGATION = "INVESTIGATION"
    ESCALATION = "ESCALATION"
    ASSET = "ASSET"
    INCIDENT = "INCIDENT"
    COVERAGE = "COVERAGE"
    ACTIVITY = "ACTIVITY"


class RiskTier(str, Enum):
    """Composite risk score classification bands."""
    LOW = "LOW"             # 0 - 25
    GUARDED = "GUARDED"     # 26 - 50
    ELEVATED = "ELEVATED"   # 51 - 75
    CRITICAL = "CRITICAL"   # 76 - 100


class TrendDirection(str, Enum):
    """Historical risk score direction."""
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DETERIORATING = "DETERIORATING"


class SubmissionStatus(str, Enum):
    """Raw ingestion batch lifecycle status."""
    PENDING = "PENDING"
    VALIDATING = "VALIDATING"
    NORMALIZED = "NORMALIZED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class FindingStatus(str, Enum):
    """Status of an analytic finding."""
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ManifestType(str, Enum):
    """Types of cryptographic audit manifests."""
    INGESTION_BATCH = "INGESTION_BATCH"
    ANALYTICS_RUN = "ANALYTICS_RUN"
    PERIODIC_AUDIT = "PERIODIC_AUDIT"


class SizeTier(str, Enum):
    """Scale classification for supervised entities."""
    TIER_1 = "Tier-1"
    TIER_2 = "Tier-2"
    TIER_3 = "Tier-3"


class SectorType(str, Enum):
    """Standardized industry sectors."""
    BANKING = "Banking"
    TELECOM = "Telecom"
    ENERGY = "Energy"
    HEALTHCARE = "Healthcare"
    FINTECH = "Fintech"
    GOVERNMENT = "Government"
    DEFENSE = "Defense"
    OTHER = "Other"
