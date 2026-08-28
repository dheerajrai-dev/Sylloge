"""Test suite for SAT-SA Audit Service & SHA-256 Merkle Root Integrity."""

from datetime import datetime, timezone
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session

from audit_service.main import app
from audit_service.manifest.generator import AuditManifestGenerator
from audit_service.manifest.verifier import AuditManifestVerifier
from shared.models.audit import AuditManifest
from shared.models.correlation import Correlation
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.schemas.audit import AuditManifestCreate


@pytest.mark.asyncio
async def test_audit_health_endpoint():
    """Validates audit service /health returns 200 HEALTHY."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["service"] == "sat-sa-audit-service"


def test_sync_audit_manifest_generator_and_verifier_empty(sync_db: Session, sample_entity: Entity):
    """Tests manifest generation and verification on empty entity."""
    start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

    create_req = AuditManifestCreate(
        entity_id=sample_entity.entity_id,
        period_start=start,
        period_end=end,
    )

    doc, db_manifest = AuditManifestGenerator.generate_manifest_sync(create_req, sync_db)

    assert doc.manifest_id == db_manifest.manifest_id
    assert doc.entity_id == sample_entity.entity_id
    assert len(doc.merkle_tree.root_sha256) == 64
    assert db_manifest.file_count == 0
    assert db_manifest.event_count == 0
    assert db_manifest.finding_count == 0

    # Verify
    result = AuditManifestVerifier.verify_manifest_sync(db_manifest.manifest_id, sync_db)
    assert result.is_valid is True
    assert result.status == "VERIFIED"
    assert len(result.discrepancies) == 0
    assert result.stored_root_sha256 == db_manifest.root_merkle_sha256


def test_sync_audit_manifest_full_components_and_tamper_detection(sync_db: Session, sample_entity: Entity):
    """Tests manifest generation with all components and asserts tamper detection upon data mutation."""
    start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)

    # 1. Add Raw Submission
    sub = RawSubmission(
        submission_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path="raw/alerts.csv",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        row_count=10,
        valid_row_count=9,
        quarantined_row_count=1,
        ingestion_status="NORMALIZED",
        uploaded_at=now,
    )
    sync_db.add(sub)

    # 2. Add Quarantined Row
    quar = QuarantinedRow(
        quarantine_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        row_index=0,
        raw_content={"raw": "bad_row"},
        failure_reason="Invalid date format",
        failed_fields=["timestamp"],
        quarantined_at=now,
    )
    sync_db.add(quar)

    # 3. Add Normalized Event
    evt = NormalizedEvent(
        event_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        submission_id=sub.submission_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        standard_event_type="ALERT",
        event_timestamp=now,
        asset_id="SRV-01",
        action="ALERT_FIRED",
        status="OPEN",
        severity="CRITICAL",
        raw_row_index=1,
        raw_ref_id="ALT-001",
        normalized_payload={"rule": "Mimikatz detected"},
    )
    sync_db.add(evt)

    # 4. Add Execution Gap Finding
    gap = ExecutionGapFinding(
        finding_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        entity_id=sample_entity.entity_id,
        rule_id="EG_01_UNINVESTIGATED_CRITICAL",
        rule_name="Uninvestigated Critical Alert",
        rule_category="TRIAGE_FAILURE",
        severity="CRITICAL",
        period_start=start,
        period_end=end,
        description="Critical alert uninvestigated for 72h",
        rationale="Alert ALT-001 has no assigned analyst",
        evidence_record_ids=[str(evt.event_id)],
        raw_evidence_refs=["ALT-001"],
        metric_values={"elapsed_hours": 72.0},
    )
    sync_db.add(gap)

    # 5. Add Risk Score
    score = RiskScore(
        score_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        entity_id=sample_entity.entity_id,
        period_start=start,
        period_end=end,
        composite_risk_score=78.5,
        execution_gap_score=85.0,
        negative_space_score=70.0,
        peer_deviation_score=75.0,
        weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
        risk_tier="CRITICAL",
        trend_direction="DETERIORATING",
        rationale_summary="High execution gap score driving risk.",
        calculated_at=now,
    )
    sync_db.add(score)
    sync_db.commit()

    # Generate Manifest
    create_req = AuditManifestCreate(
        entity_id=sample_entity.entity_id,
        period_start=start,
        period_end=end,
    )
    doc, db_manifest = AuditManifestGenerator.generate_manifest_sync(create_req, sync_db)

    assert db_manifest.file_count == 1
    assert db_manifest.event_count == 1
    assert db_manifest.finding_count == 1
    assert doc.components.findings_summary.composite_risk_score == 78.5

    # Verify Initial State
    res = AuditManifestVerifier.verify_manifest_sync(db_manifest.manifest_id, sync_db)
    assert res.is_valid is True
    assert res.status == "VERIFIED"

    # TAMPER TEST: Modify a field in normalized events
    evt.action = "TAMPERED_ACTION"
    sync_db.commit()

    tamper_res = AuditManifestVerifier.verify_manifest_sync(db_manifest.manifest_id, sync_db)
    assert tamper_res.is_valid is False
    assert tamper_res.status == "TAMPER_DETECTED"
    assert len(tamper_res.discrepancies) > 0
    assert any("Normalized events subtree mismatch" in d for d in tamper_res.discrepancies)


@pytest.mark.asyncio
async def test_audit_api_workflow_async(async_db, auth_headers):
    """Tests the full audit API endpoints via HTTP calls."""
    from shared.db.session import get_db

    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="TEST_ENTITY",
        name="Test Entity Corp",
        sector="Banking",
        size_tier="Tier-1",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.commit()

    start = datetime(2026, 8, 1, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    end = datetime(2026, 8, 31, 23, 59, 59, tzinfo=timezone.utc).isoformat()

    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Generate manifest
        payload = {
            "entity_id": str(entity.entity_id),
            "period_start": start,
            "period_end": end,
            "manifest_type": "PERIODIC_AUDIT",
        }
        gen_res = await client.post("/api/v1/audit/manifest", json=payload, headers=auth_headers)
        assert gen_res.status_code == 201
        manifest_data = gen_res.json()
        manifest_id = manifest_data["manifest_id"]
        assert manifest_data["root_merkle_sha256"] is not None

        # Verify manifest
        verify_res = await client.post(
            "/api/v1/audit/verify",
            json={"manifest_id": manifest_id},
            headers=auth_headers,
        )
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["is_valid"] is True
        assert verify_data["status"] == "VERIFIED"

        # Get Manifest by ID
        get_res = await client.get(f"/api/v1/audit/manifest/{manifest_id}")
        assert get_res.status_code == 200
        assert get_res.json()["manifest_id"] == manifest_id

        # Get Latest by Entity
        latest_res = await client.get(f"/api/v1/audit/manifest/entity/{entity.entity_id}/latest")
        assert latest_res.status_code == 200
        assert latest_res.json()["manifest_id"] == manifest_id

        # List Manifests
        list_res = await client.get(f"/api/v1/audit/manifests?entity_id={entity.entity_id}")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

    app.dependency_overrides.clear()

