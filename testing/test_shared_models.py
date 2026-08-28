"""Unit tests for all 13 SQLAlchemy ORM Models in SAT-SA."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models.audit import AuditManifest
from shared.models.benchmark import PeerBenchmark
from shared.models.correlation import Correlation
from shared.models.dataset import Dataset
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.mapping import FieldMappingProfile
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.models.user import User


def test_user_model_crud(sync_db: Session):
    """Verifies User model CRUD and unique constraints."""
    user = User(
        username="supervisor_test",
        password_hash="$2b$12$hashedpasswordstring",
        full_name="Alex River",
        role="supervisor",
        is_active=True,
    )
    sync_db.add(user)
    sync_db.commit()

    queried = sync_db.query(User).filter_by(username="supervisor_test").first()
    assert queried is not None
    assert queried.full_name == "Alex River"
    assert queried.role == "supervisor"
    assert queried.is_active is True
    assert isinstance(queried.user_id, uuid.UUID)

    # Unique constraint test
    duplicate_user = User(
        username="supervisor_test",
        password_hash="$2b$12$otherhash",
        full_name="Duplicate",
        role="supervisor",
    )
    sync_db.add(duplicate_user)
    with pytest.raises(IntegrityError):
        sync_db.commit()
    sync_db.rollback()


def test_entity_model_crud(sync_db: Session):
    """Verifies Entity model CRUD and metadata storage."""
    entity = Entity(
        entity_code="TELCO_GAMMA",
        name="Gamma Telecom Networks",
        sector="Telecom",
        size_tier="Tier-2",
        contact_email="ops@gamma.internal",
        is_active=True,
        entity_metadata={"asn": 12345, "primary_dc": "DC-East"},
    )
    sync_db.add(entity)
    sync_db.commit()

    queried = sync_db.query(Entity).filter_by(entity_code="TELCO_GAMMA").first()
    assert queried is not None
    assert queried.name == "Gamma Telecom Networks"
    assert queried.sector == "Telecom"
    assert queried.size_tier == "Tier-2"
    assert queried.entity_metadata["asn"] == 12345


def test_field_mapping_profile_model(sync_db: Session, sample_entity: Entity):
    """Verifies FieldMappingProfile model and foreign key relationship."""
    profile = FieldMappingProfile(
        entity_id=sample_entity.entity_id,
        dataset_type="case_management",
        version=1,
        mapping_rules={"src_case_id": "case_id", "src_status": "status"},
        transform_rules={"date_format": "ISO8601"},
        is_active=True,
    )
    sync_db.add(profile)
    sync_db.commit()

    queried = sync_db.query(FieldMappingProfile).filter_by(profile_id=profile.profile_id).first()
    assert queried is not None
    assert queried.entity_id == sample_entity.entity_id
    assert queried.entity.entity_code == "BANK_ALPHA"
    assert queried.mapping_rules["src_case_id"] == "case_id"


def test_dataset_catalog_model(sync_db: Session, sample_entity: Entity):
    """Verifies Dataset catalog model."""
    dataset = Dataset(
        entity_id=sample_entity.entity_id,
        dataset_type="asset_inventory",
        display_name="Core IT Assets",
        description="Inventory of all managed endpoints and servers",
        schema_version="1.0",
    )
    sync_db.add(dataset)
    sync_db.commit()

    queried = sync_db.query(Dataset).filter_by(dataset_id=dataset.dataset_id).first()
    assert queried is not None
    assert queried.display_name == "Core IT Assets"
    assert queried.entity.name == sample_entity.name


def test_raw_submission_model(sync_db: Session, sample_entity: Entity):
    """Verifies RawSubmission model."""
    sub = RawSubmission(
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts_202608.csv",
        file_size_bytes=1048576,
        mime_type="text/csv",
        minio_raw_path="c1f7a420/alert_metadata/2026/08/alerts_202608.csv",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        row_count=500,
        valid_row_count=490,
        quarantined_row_count=10,
        ingestion_status="NORMALIZED",
    )
    sync_db.add(sub)
    sync_db.commit()

    queried = sync_db.query(RawSubmission).filter_by(submission_id=sub.submission_id).first()
    assert queried is not None
    assert queried.valid_row_count == 490
    assert queried.quarantined_row_count == 10
    assert queried.ingestion_status == "NORMALIZED"


def test_quarantined_row_model(sync_db: Session, sample_entity: Entity):
    """Verifies QuarantinedRow model with payload preservation."""
    sub = RawSubmission(
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path="test_path.csv",
        sha256_hash="dummyhash",
    )
    sync_db.add(sub)
    sync_db.commit()

    q_row = QuarantinedRow(
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        row_index=42,
        raw_content={"alert_id": "ALT-999", "timestamp": "MALFORMED_TIMESTAMP"},
        failure_reason="Invalid timestamp format: 'MALFORMED_TIMESTAMP'",
        failed_fields=["timestamp"],
    )
    sync_db.add(q_row)
    sync_db.commit()

    queried = sync_db.query(QuarantinedRow).filter_by(quarantine_id=q_row.quarantine_id).first()
    assert queried is not None
    assert queried.row_index == 42
    assert "timestamp" in queried.failed_fields
    assert queried.raw_content["alert_id"] == "ALT-999"


def test_normalized_event_model(sync_db: Session, sample_entity: Entity):
    """Verifies NormalizedEvent model with canonical attributes."""
    sub = RawSubmission(
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path="test_path.csv",
        sha256_hash="dummyhash2",
    )
    sync_db.add(sub)
    sync_db.commit()

    now = datetime.now(timezone.utc)
    event = NormalizedEvent(
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        standard_event_type="ALERT",
        event_timestamp=now,
        asset_id="SRV-PROD-01",
        user_id="analyst_jdoe",
        action="BRUTE_FORCE_DETECTED",
        status="OPEN",
        severity="HIGH",
        source_ip="192.168.1.50",
        destination_ip="10.0.0.1",
        raw_row_index=0,
        raw_ref_id="ALT-1001",
        normalized_payload={"rule_id": "R-101", "signature": "Auth_Failed_x10"},
    )
    sync_db.add(event)
    sync_db.commit()

    queried = sync_db.query(NormalizedEvent).filter_by(event_id=event.event_id).first()
    assert queried is not None
    assert queried.asset_id == "SRV-PROD-01"
    assert queried.severity == "HIGH"
    assert queried.normalized_payload["signature"] == "Auth_Failed_x10"


def test_execution_gap_finding_model(sync_db: Session, sample_entity: Entity):
    """Verifies ExecutionGapFinding model and evidence linkage."""
    now = datetime.now(timezone.utc)
    finding = ExecutionGapFinding(
        entity_id=sample_entity.entity_id,
        rule_id="GAP_01_UNINVESTIGATED_CRITICAL",
        rule_name="Uninvestigated Critical Alert",
        rule_category="TRIAGE_FAILURE",
        severity="CRITICAL",
        period_start=now,
        period_end=now,
        status="OPEN",
        description="Critical alert was not assigned or investigated within 24 hours.",
        rationale="Alert ALT-1001 remained in OPEN status for 72.5 hours without analyst triage.",
        evidence_record_ids=["c1f7a420-0000-0000-0000-000000000001"],
        raw_evidence_refs=["ALT-1001"],
        metric_values={"elapsed_hours": 72.5, "sla_hours": 24.0},
    )
    sync_db.add(finding)
    sync_db.commit()

    queried = sync_db.query(ExecutionGapFinding).filter_by(finding_id=finding.finding_id).first()
    assert queried is not None
    assert queried.rule_id == "GAP_01_UNINVESTIGATED_CRITICAL"
    assert queried.severity == "CRITICAL"
    assert queried.metric_values["elapsed_hours"] == 72.5


def test_negative_space_finding_model(sync_db: Session, sample_entity: Entity):
    """Verifies NegativeSpaceFinding model."""
    now = datetime.now(timezone.utc)
    finding = NegativeSpaceFinding(
        entity_id=sample_entity.entity_id,
        check_id="NEG_01_ZERO_ALERT_SILENCE",
        check_name="Sensor Silence Detection",
        check_category="LOG_SILENCE",
        severity="HIGH",
        period_start=now,
        period_end=now,
        expected_volume=500.0,
        observed_volume=0.0,
        drop_percentage=100.0,
        entropy_score=0.0,
        rationale="Zero alerts received during active business hours for Core Banking network.",
        evidence_record_ids=[],
    )
    sync_db.add(finding)
    sync_db.commit()

    queried = sync_db.query(NegativeSpaceFinding).filter_by(finding_id=finding.finding_id).first()
    assert queried is not None
    assert queried.check_id == "NEG_01_ZERO_ALERT_SILENCE"
    assert queried.drop_percentage == 100.0


def test_correlation_model(sync_db: Session, sample_entity: Entity):
    """Verifies Correlation model linking two normalized events."""
    sub = RawSubmission(
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path="test_path.csv",
        sha256_hash="dummyhash3",
    )
    sync_db.add(sub)
    sync_db.commit()

    now = datetime.now(timezone.utc)
    e1 = NormalizedEvent(
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        standard_event_type="ALERT",
        event_timestamp=now,
        raw_row_index=0,
    )
    e2 = NormalizedEvent(
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        standard_event_type="ALERT",
        event_timestamp=now,
        raw_row_index=1,
    )
    sync_db.add_all([e1, e2])
    sync_db.commit()

    corr = Correlation(
        entity_id=sample_entity.entity_id,
        correlation_type="REPEAT_ASSET_ALERT",
        primary_event_id=e1.event_id,
        correlated_event_id=e2.event_id,
        asset_id="HOST-101",
        similarity_score=0.95,
        shared_attributes={"rule": "PORT_SCAN"},
        rationale="Multiple repeat port scan alerts on same host within 24 hours.",
    )
    sync_db.add(corr)
    sync_db.commit()

    queried = sync_db.query(Correlation).filter_by(correlation_id=corr.correlation_id).first()
    assert queried is not None
    assert queried.similarity_score == 0.95
    assert queried.primary_event.event_id == e1.event_id
    assert queried.correlated_event.event_id == e2.event_id


def test_peer_benchmark_model(sync_db: Session):
    """Verifies PeerBenchmark model."""
    now = datetime.now(timezone.utc)
    benchmark = PeerBenchmark(
        sector="Banking",
        size_tier="Tier-1",
        metric_name="mttd_hours",
        period_start=now,
        period_end=now,
        peer_group_size=5,
        mean_val=4.2,
        std_dev=1.1,
        p25=3.0,
        p50=4.0,
        p75=5.2,
        p90=6.1,
        is_low_confidence=False,
    )
    sync_db.add(benchmark)
    sync_db.commit()

    queried = sync_db.query(PeerBenchmark).filter_by(benchmark_id=benchmark.benchmark_id).first()
    assert queried is not None
    assert queried.sector == "Banking"
    assert queried.peer_group_size == 5
    assert queried.is_low_confidence is False


def test_risk_score_model(sync_db: Session, sample_entity: Entity):
    """Verifies RiskScore model and composite calculations."""
    now = datetime.now(timezone.utc)
    score = RiskScore(
        entity_id=sample_entity.entity_id,
        period_start=now,
        period_end=now,
        composite_risk_score=68.5,
        execution_gap_score=80.0,
        negative_space_score=65.0,
        peer_deviation_score=50.0,
        weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
        risk_tier="ELEVATED",
        trend_direction="STABLE",
        rationale_summary="High volume of uninvestigated critical alerts driving elevated risk posture.",
    )
    sync_db.add(score)
    sync_db.commit()

    queried = sync_db.query(RiskScore).filter_by(score_id=score.score_id).first()
    assert queried is not None
    assert queried.composite_risk_score == 68.5
    assert queried.risk_tier == "ELEVATED"
    assert queried.weights_applied["execution_gap"] == 0.45


def test_audit_manifest_model(sync_db: Session, sample_entity: Entity):
    """Verifies AuditManifest model."""
    now = datetime.now(timezone.utc)
    manifest = AuditManifest(
        entity_id=sample_entity.entity_id,
        period_start=now,
        period_end=now,
        manifest_type="PERIODIC_AUDIT",
        root_merkle_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_count=3,
        event_count=1500,
        finding_count=6,
        minio_manifest_path="c1f7a420/manifests/2026/08/manifest_001.json",
        component_hashes={"raw_sha": "aaaa", "events_sha": "bbbb"},
    )
    sync_db.add(manifest)
    sync_db.commit()

    queried = sync_db.query(AuditManifest).filter_by(manifest_id=manifest.manifest_id).first()
    assert queried is not None
    assert queried.root_merkle_sha256 == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert queried.event_count == 1500
