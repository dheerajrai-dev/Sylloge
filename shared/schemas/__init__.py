"""Pydantic v2 schemas for SAT-SA."""

from shared.schemas.audit import (
    AuditManifestCreate,
    AuditManifestDocument,
    AuditManifestOut,
    AuditVerificationResult,
    FindingsComponentSummary,
    ManifestComponentsDTO,
    MerkleSubtreesDTO,
    MerkleTreeDTO,
    NormalizedComponentSummary,
    QuarantineComponentSummary,
    RawSubmissionComponent,
)
from shared.schemas.auth import (
    LoginRequest,
    TokenPayload,
    TokenResponse,
    UserCreate,
    UserOut,
)
from shared.schemas.benchmark import (
    BenchmarkCohortSummary,
    PeerBenchmarkBase,
    PeerBenchmarkCreate,
    PeerBenchmarkOut,
)
from shared.schemas.correlation import (
    CorrelationBase,
    CorrelationCreate,
    CorrelationOut,
)
from shared.schemas.dataset import (
    DatasetBase,
    DatasetCreate,
    DatasetOut,
)
from shared.schemas.datasets import (
    AlertMetadataSchema,
    AnalystActivitySchema,
    AssetInventorySchema,
    CaseManagementSchema,
    CoverageReportSchema,
    EscalationRecordSchema,
    IncidentReportSchema,
    InvestigationRecordSchema,
)
from shared.schemas.entity import (
    EntityBase,
    EntityCreate,
    EntityOut,
    EntitySummary,
    EntityUpdate,
)
from shared.schemas.event import (
    EventFilterParams,
    StandardEventCreate,
    StandardEventOut,
)
from shared.schemas.finding import (
    ExecutionGapFindingOut,
    FindingFilterParams,
    NegativeSpaceFindingOut,
    RationaleCard,
)
from shared.schemas.mapping import (
    FieldMappingProfileBase,
    FieldMappingProfileCreate,
    FieldMappingProfileOut,
    FieldMappingProfileUpdate,
)
from shared.schemas.quarantine import (
    QuarantinedRowOut,
    QuarantineSummary,
)
from shared.schemas.risk_score import (
    RiskBreakdown,
    RiskScoreCalculateRequest,
    RiskScoreOut,
)
from shared.schemas.submission import (
    IngestRequest,
    IngestResult,
    SubmissionBase,
    SubmissionCreate,
    SubmissionOut,
)

__all__ = [
    # Auth
    "LoginRequest",
    "TokenResponse",
    "TokenPayload",
    "UserOut",
    "UserCreate",
    # Entity
    "EntityBase",
    "EntityCreate",
    "EntityUpdate",
    "EntityOut",
    "EntitySummary",
    # Mapping
    "FieldMappingProfileBase",
    "FieldMappingProfileCreate",
    "FieldMappingProfileUpdate",
    "FieldMappingProfileOut",
    # Dataset
    "DatasetBase",
    "DatasetCreate",
    "DatasetOut",
    # Submission
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionOut",
    "IngestRequest",
    "IngestResult",
    # Quarantine
    "QuarantinedRowOut",
    "QuarantineSummary",
    # Event
    "StandardEventCreate",
    "StandardEventOut",
    "EventFilterParams",
    # Finding
    "RationaleCard",
    "ExecutionGapFindingOut",
    "NegativeSpaceFindingOut",
    "FindingFilterParams",
    # Correlation
    "CorrelationBase",
    "CorrelationCreate",
    "CorrelationOut",
    # Benchmark
    "PeerBenchmarkBase",
    "PeerBenchmarkCreate",
    "PeerBenchmarkOut",
    "BenchmarkCohortSummary",
    # Risk Score
    "RiskBreakdown",
    "RiskScoreCalculateRequest",
    "RiskScoreOut",
    # Audit
    "MerkleSubtreesDTO",
    "MerkleTreeDTO",
    "RawSubmissionComponent",
    "QuarantineComponentSummary",
    "NormalizedComponentSummary",
    "FindingsComponentSummary",
    "ManifestComponentsDTO",
    "AuditManifestDocument",
    "AuditManifestCreate",
    "AuditManifestOut",
    "AuditVerificationResult",
    # Datasets
    "AlertMetadataSchema",
    "CaseManagementSchema",
    "InvestigationRecordSchema",
    "EscalationRecordSchema",
    "AssetInventorySchema",
    "IncidentReportSchema",
    "CoverageReportSchema",
    "AnalystActivitySchema",
]
