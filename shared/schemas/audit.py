"""Audit manifest and Merkle verification schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import ManifestType


class MerkleSubtreesDTO(BaseModel):
    """Subtree hashes forming the Merkle root."""
    raw_submissions_sha256: str
    quarantined_records_sha256: str
    normalized_events_sha256: str
    findings_and_scores_sha256: str


class MerkleTreeDTO(BaseModel):
    """Merkle tree digest container."""
    root_sha256: str
    subtrees: MerkleSubtreesDTO


class RawSubmissionComponent(BaseModel):
    submission_id: str
    file_name: str
    sha256_hash: str
    row_count: int
    minio_path: str


class QuarantineComponentSummary(BaseModel):
    total_quarantined: int
    sha256_digest: str


class NormalizedComponentSummary(BaseModel):
    total_events: int
    sha256_digest: str


class FindingsComponentSummary(BaseModel):
    execution_gap_count: int
    negative_space_count: int
    correlations_count: int
    composite_risk_score: Optional[float] = None
    sha256_digest: str


class ManifestComponentsDTO(BaseModel):
    raw_submissions: List[RawSubmissionComponent] = Field(default_factory=list)
    quarantine_summary: QuarantineComponentSummary
    normalized_summary: NormalizedComponentSummary
    findings_summary: FindingsComponentSummary


class AuditManifestDocument(BaseModel):
    """Verbatim signed JSON structure saved in MinIO `audit-manifests` bucket."""
    manifest_version: str = "1.0.0"
    manifest_id: uuid.UUID
    entity_id: uuid.UUID
    entity_code: str
    period: Dict[str, datetime]
    generator_service: str = "sat-sa-audit-service v1.0.0"
    algorithm: str = "SHA-256"
    generated_at: datetime
    merkle_tree: MerkleTreeDTO
    components: ManifestComponentsDTO


class AuditManifestCreate(BaseModel):
    """Payload to trigger audit manifest compilation."""
    entity_id: uuid.UUID
    submission_id: Optional[uuid.UUID] = None
    period_start: datetime
    period_end: datetime
    manifest_type: ManifestType = ManifestType.PERIODIC_AUDIT


class AuditManifestOut(BaseModel):
    """Response DTO for audit manifest DB record."""
    model_config = ConfigDict(from_attributes=True)

    manifest_id: uuid.UUID
    entity_id: uuid.UUID
    submission_id: Optional[uuid.UUID] = None
    period_start: datetime
    period_end: datetime
    manifest_type: str
    root_merkle_sha256: str
    file_count: int
    event_count: int
    finding_count: int
    minio_manifest_path: str
    component_hashes: Dict[str, Any]
    generated_at: datetime


class AuditVerificationResult(BaseModel):
    """Result of Merkle root cryptographic integrity verification."""
    manifest_id: uuid.UUID
    entity_id: uuid.UUID
    is_valid: bool
    status: str  # "VERIFIED" or "TAMPER_DETECTED"
    stored_root_sha256: str
    recomputed_root_sha256: str
    discrepancies: List[str] = Field(default_factory=list)
    verified_at: datetime
