"""Unit tests for Pydantic v2 schemas and dataset schemas in SAT-SA."""

import uuid
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from shared.events.enums import DatasetType, RiskTier, SeverityTier, StandardEventType
from shared.events.standard_event import StandardEvent
from shared.schemas.audit import (
    AuditManifestCreate,
    AuditManifestDocument,
    AuditVerificationResult,
    FindingsComponentSummary,
    ManifestComponentsDTO,
    MerkleSubtreesDTO,
    MerkleTreeDTO,
    NormalizedComponentSummary,
    QuarantineComponentSummary,
    RawSubmissionComponent,
)
from shared.schemas.auth import LoginRequest, TokenPayload, TokenResponse, UserCreate, UserOut
from shared.schemas.benchmark import PeerBenchmarkCreate, PeerBenchmarkOut
from shared.schemas.correlation import CorrelationCreate, CorrelationOut
from shared.schemas.dataset import DatasetCreate, DatasetOut
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
from shared.schemas.entity import EntityCreate, EntityOut, EntitySummary, EntityUpdate
from shared.schemas.event import StandardEventCreate, StandardEventOut
from shared.schemas.finding import ExecutionGapFindingOut, NegativeSpaceFindingOut, RationaleCard
from shared.schemas.mapping import FieldMappingProfileCreate, FieldMappingProfileOut
from shared.schemas.quarantine import QuarantinedRowOut, QuarantineSummary
from shared.schemas.risk_score import RiskBreakdown, RiskScoreCalculateRequest, RiskScoreOut
from shared.schemas.submission import IngestRequest, IngestResult, SubmissionCreate, SubmissionOut


def test_auth_schemas():
    """Verifies Auth schemas validation."""
    login_req = LoginRequest(username="supervisor", password="secure_password_123")
    assert login_req.username == "supervisor"

    with pytest.raises(ValidationError):
        LoginRequest(username="ab", password="123")  # too short

    user_out = UserOut(
        user_id=uuid.uuid4(),
        username="supervisor",
        full_name="Chief Inspector",
        role="supervisor",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    assert user_out.username == "supervisor"

    token_resp = TokenResponse(
        access_token="sample.jwt.token",
        token_type="bearer",
        expires_in=86400,
        user=user_out,
    )
    assert token_resp.expires_in == 86400


def test_entity_schemas():
    """Verifies Entity schemas."""
    entity_create = EntityCreate(
        entity_code="BANK_DELTA",
        name="Delta State Bank",
        sector="Banking",
        size_tier="Tier-2",
        contact_email="soc@delta.internal",
        is_active=True,
        entity_metadata={"branch_count": 45},
    )
    assert entity_create.entity_code == "BANK_DELTA"

    entity_out = EntityOut(
        entity_id=uuid.uuid4(),
        entity_code="BANK_DELTA",
        name="Delta State Bank",
        sector="Banking",
        size_tier="Tier-2",
        contact_email="soc@delta.internal",
        is_active=True,
        entity_metadata={"branch_count": 45},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert entity_out.entity_code == "BANK_DELTA"


def test_standard_event_schema():
    """Verifies canonical StandardEvent schema and defaults."""
    now = datetime.now(timezone.utc)
    evt_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    ent_id = uuid.uuid4()

    event = StandardEvent(
        event_id=evt_id,
        submission_id=sub_id,
        entity_id=ent_id,
        dataset_type=DatasetType.ALERT_METADATA,
        standard_event_type=StandardEventType.ALERT,
        event_timestamp=now,
        asset_id="HOST-99",
        action="PORT_SCAN",
        severity=SeverityTier.HIGH,
        raw_row_index=5,
        normalized_payload={"port": 445, "protocol": "TCP"},
    )
    assert event.event_id == evt_id
    assert event.severity == SeverityTier.HIGH
    assert event.normalized_payload["port"] == 445


def test_eight_dataset_schemas():
    """Verifies parsing across all 8 supported dataset telemetry types."""
    now = datetime.now(timezone.utc)

    # 1. AlertMetadata
    alert = AlertMetadataSchema(
        alert_id="ALT-101",
        timestamp=now,
        rule_name="Unusual_Outbound_Traffic",
        severity="HIGH",
        source_ip="10.0.1.5",
        destination_ip="198.51.100.2",
        asset_id="WS-001",
    )
    assert alert.alert_id == "ALT-101"

    # 2. CaseManagement
    case = CaseManagementSchema(
        case_id="CASE-500",
        created_at=now,
        status="INVESTIGATING",
        priority="P1_CRITICAL",
        title="Ransomware lateral movement alert",
    )
    assert case.case_id == "CASE-500"

    # 3. InvestigationRecord
    inv = InvestigationRecordSchema(
        investigation_id="INV-001",
        case_id="CASE-500",
        analyst_id="ANALYST_07",
        timestamp=now,
        investigation_action="MEMORY_DUMP_ANALYZED",
        notes="Identified malicious powershell process running from temp dir.",
    )
    assert inv.investigation_id == "INV-001"

    # 4. EscalationRecord
    esc = EscalationRecordSchema(
        escalation_id="ESC-10",
        case_id="CASE-500",
        escalated_from="SOC_L1",
        escalated_to="IR_LEAD",
        timestamp=now,
        escalation_reason="Confirmed host compromise on domain controller.",
    )
    assert esc.escalated_to == "IR_LEAD"

    # 5. AssetInventory
    asset = AssetInventorySchema(
        asset_id="DC-PRIMARY",
        hostname="dc01.corp.internal",
        ip_address="10.0.0.5",
        asset_type="DOMAIN_CONTROLLER",
        criticality="TIER_1",
        is_monitored=True,
    )
    assert asset.is_monitored is True

    # 6. IncidentReport
    inc = IncidentReportSchema(
        incident_id="INC-2026-003",
        title="Unauthorized credential dump attempt",
        severity="CRITICAL",
        declared_at=now,
        affected_assets=["dc01.corp.internal"],
    )
    assert inc.severity == "CRITICAL"

    # 7. CoverageReport
    cov = CoverageReportSchema(
        coverage_id="COV-01",
        tool_name="EDR_Agent",
        source_type="ENDPOINT_LOGS",
        total_assets_monitored=1200,
        active_sensors=1180,
        coverage_percentage=98.33,
        reported_at=now,
    )
    assert cov.coverage_percentage == 98.33

    # 8. AnalystActivity
    act = AnalystActivitySchema(
        activity_id="ACT-881",
        analyst_id="ANALYST_07",
        activity_type="LOG_SEARCH",
        timestamp=now,
        duration_seconds=420,
    )
    assert act.duration_seconds == 420


def test_audit_manifest_document_schema():
    """Verifies complete cryptographic audit manifest document schema."""
    now = datetime.now(timezone.utc)
    doc = AuditManifestDocument(
        manifest_id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
        entity_code="BANK_ALPHA",
        period={"start": now, "end": now},
        generated_at=now,
        merkle_tree=MerkleTreeDTO(
            root_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            subtrees=MerkleSubtreesDTO(
                raw_submissions_sha256="aaaa" * 16,
                quarantined_records_sha256="bbbb" * 16,
                normalized_events_sha256="cccc" * 16,
                findings_and_scores_sha256="dddd" * 16,
            ),
        ),
        components=ManifestComponentsDTO(
            raw_submissions=[
                RawSubmissionComponent(
                    submission_id=str(uuid.uuid4()),
                    file_name="test.csv",
                    sha256_hash="e3b0c442" * 8,
                    row_count=100,
                    minio_path="test/path.csv",
                )
            ],
            quarantine_summary=QuarantineComponentSummary(
                total_quarantined=2,
                sha256_digest="1111" * 16,
            ),
            normalized_summary=NormalizedComponentSummary(
                total_events=98,
                sha256_digest="2222" * 16,
            ),
            findings_summary=FindingsComponentSummary(
                execution_gap_count=1,
                negative_space_count=0,
                correlations_count=3,
                composite_risk_score=45.2,
                sha256_digest="3333" * 16,
            ),
        ),
    )
    assert doc.entity_code == "BANK_ALPHA"
    assert doc.merkle_tree.root_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
