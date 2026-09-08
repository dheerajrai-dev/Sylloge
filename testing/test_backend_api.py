"""Comprehensive Integration Test Suite for SAT-SA Backend API Gateway (Port 8000)."""

from datetime import datetime, timezone
import io
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app
from shared.auth.jwt import create_access_token
from shared.auth.security import hash_password
from shared.db.session import get_db
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.models.user import User


@pytest.fixture
def supervisor_headers():
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        username="supervisor",
        role="supervisor",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_backend_health():
    """Validates backend /health returns 200 HEALTHY."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["service"] == "sat-sa-backend-gateway"


@pytest.mark.asyncio
async def test_auth_login_and_me(async_db):
    """Tests supervisor login, JWT generation, and /me profile retrieval."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    # 1. Seed user
    user = User(
        user_id=uuid.uuid4(),
        username="lead_supervisor",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Lead Cyber Inspector",
        role="supervisor",
        is_active=True,
    )
    async_db.add(user)
    await async_db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Valid Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "lead_supervisor", "password": "SuperSecret123!"},
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        assert token_data["user"]["username"] == "lead_supervisor"

        token = token_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. GET /me
        me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "lead_supervisor"

        # 4. Invalid Login
        bad_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "lead_supervisor", "password": "WrongPassword!"},
        )
        assert bad_res.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_entities_crud_and_scores(async_db, supervisor_headers):
    """Tests entity creation, listing, detail, scores, history, and radar endpoints."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Entity
        entity_payload = {
            "entity_code": "BANK_OMEGA",
            "name": "Omega International Bank",
            "sector": "Banking",
            "size_tier": "Tier-1",
            "contact_email": "soc@bankomega.internal",
            "is_active": True,
        }
        create_res = await client.post("/api/v1/entities", json=entity_payload, headers=supervisor_headers)
        assert create_res.status_code == 201
        ent_data = create_res.json()
        entity_id = ent_data["entity_id"]

        # 2. List Entities
        list_res = await client.get("/api/v1/entities", headers=supervisor_headers)
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 3. Add a RiskScore
        score = RiskScore(
            score_id=uuid.uuid4(),
            entity_id=uuid.UUID(entity_id),
            period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
            composite_risk_score=72.0,
            execution_gap_score=80.0,
            negative_space_score=65.0,
            peer_deviation_score=70.0,
            weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
            risk_tier="ELEVATED",
            trend_direction="STABLE",
            rationale_summary="Elevated risk score due to uninvestigated alerts.",
            calculated_at=datetime.now(timezone.utc),
        )
        async_db.add(score)
        await async_db.commit()

        # 4. Get Detail
        detail_res = await client.get(f"/api/v1/entities/{entity_id}", headers=supervisor_headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["latest_risk_score"] == 72.0

        # 5. Get Scores
        scores_res = await client.get(f"/api/v1/entities/{entity_id}/scores", headers=supervisor_headers)
        assert scores_res.status_code == 200
        assert len(scores_res.json()) == 2

        # 6. Get History
        hist_res = await client.get(f"/api/v1/entities/{entity_id}/history", headers=supervisor_headers)
        assert hist_res.status_code == 200
        assert len(hist_res.json()) == 2

        # 7. Get Radar
        radar_res = await client.get(f"/api/v1/entities/{entity_id}/radar", headers=supervisor_headers)
        assert radar_res.status_code == 200
        assert len(radar_res.json()) == 6

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_summary_and_worklist(async_db, supervisor_headers):
    """Tests summary KPIs and prioritized worklist ranking."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    # Seed 2 entities with different scores
    ent1 = Entity(
        entity_id=uuid.uuid4(),
        entity_code="ENT_HIGH",
        name="High Risk Energy Corp",
        sector="Energy",
        size_tier="Tier-1",
        is_active=True,
    )
    ent2 = Entity(
        entity_id=uuid.uuid4(),
        entity_code="ENT_LOW",
        name="Low Risk Credit Union",
        sector="Banking",
        size_tier="Tier-2",
        is_active=True,
    )
    async_db.add_all([ent1, ent2])
    await async_db.flush()

    sc1 = RiskScore(
        score_id=uuid.uuid4(),
        entity_id=ent1.entity_id,
        period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
        composite_risk_score=88.0,
        execution_gap_score=90.0,
        negative_space_score=85.0,
        peer_deviation_score=90.0,
        weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
        risk_tier="CRITICAL",
        trend_direction="DETERIORATING",
        rationale_summary="Critical findings.",
        calculated_at=datetime.now(timezone.utc),
    )
    sc2 = RiskScore(
        score_id=uuid.uuid4(),
        entity_id=ent2.entity_id,
        period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
        composite_risk_score=22.0,
        execution_gap_score=15.0,
        negative_space_score=20.0,
        peer_deviation_score=35.0,
        weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
        risk_tier="LOW",
        trend_direction="IMPROVING",
        rationale_summary="Compliant posture.",
        calculated_at=datetime.now(timezone.utc),
    )
    async_db.add_all([sc1, sc2])
    await async_db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Summary
        sum_res = await client.get("/api/v1/dashboard/summary", headers=supervisor_headers)
        assert sum_res.status_code == 200
        sum_data = sum_res.json()
        assert sum_data["total_entities"] >= 2
        assert sum_data["critical_risk_entities"] >= 1

        # 2. Worklist - ENT_HIGH must be ranked first (88.0 > 22.0)
        wl_res = await client.get("/api/v1/dashboard/worklist", headers=supervisor_headers)
        assert wl_res.status_code == 200
        wl_items = wl_res.json()
        assert len(wl_items) >= 2
        assert wl_items[0]["entity_id"] == str(ent1.entity_id)
        assert wl_items[0]["composite_risk_score"] == 88.0

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_findings_drilldown_and_evidence(async_db, supervisor_headers):
    """Tests findings listing, detail with rationale card, and evidence retrieval."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="FIND_CORP",
        name="Finding Corp",
        sector="Telecom",
        size_tier="Tier-1",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.flush()

    evt = NormalizedEvent(
        event_id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        entity_id=entity.entity_id,
        dataset_type="alert_metadata",
        standard_event_type="ALERT",
        event_timestamp=datetime.now(timezone.utc),
        asset_id="SRV-TEL-01",
        action="ALERT_FIRED",
        status="OPEN",
        severity="CRITICAL",
        raw_row_index=1,
        raw_ref_id="ALT-FIND-01",
        normalized_payload={"details": "Port scan detected"},
    )
    async_db.add(evt)
    await async_db.flush()

    gap = ExecutionGapFinding(
        finding_id=uuid.uuid4(),
        entity_id=entity.entity_id,
        rule_id="EG_01_UNINVESTIGATED_CRITICAL",
        rule_name="Uninvestigated Critical Alert",
        rule_category="TRIAGE_FAILURE",
        severity="CRITICAL",
        period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
        description="Critical alert ALT-FIND-01 uninvestigated",
        rationale="Alert was not assigned within SLA",
        evidence_record_ids=[str(evt.event_id)],
        raw_evidence_refs=["ALT-FIND-01"],
        metric_values={"elapsed_hours": 72.0},
    )
    async_db.add(gap)
    await async_db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List findings
        f_res = await client.get("/api/v1/findings", headers=supervisor_headers)
        assert f_res.status_code == 200
        assert len(f_res.json()) >= 1

        # 2. Finding detail
        detail_res = await client.get(f"/api/v1/findings/{gap.finding_id}", headers=supervisor_headers)
        assert detail_res.status_code == 200
        data = detail_res.json()
        assert data["finding"]["finding_id"] == str(gap.finding_id)
        assert data["rationale_card"]["severity"] == "CRITICAL"

        # 3. Evidence events
        ev_res = await client.get(f"/api/v1/findings/{gap.finding_id}/evidence", headers=supervisor_headers)
        assert ev_res.status_code == 200
        assert len(ev_res.json()) == 1
        assert ev_res.json()[0]["raw_ref_id"] == "ALT-FIND-01"

        # 4. Raw diff
        diff_res = await client.get(f"/api/v1/findings/{gap.finding_id}/raw-diff", headers=supervisor_headers)
        assert diff_res.status_code == 200
        assert len(diff_res.json()["normalized_events"]) == 1

        # 5. Acknowledge
        ack_res = await client.post(f"/api/v1/findings/{gap.finding_id}/acknowledge", headers=supervisor_headers)
        assert ack_res.status_code == 200
        assert ack_res.json()["status"] == "SUCCESS"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_submissions_upload_and_quarantine(async_db, supervisor_headers):
    """Tests file submission upload, parsing, quarantine, and normalization."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="UPLOAD_CORP",
        name="Upload Corp",
        sector="Banking",
        size_tier="Tier-1",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.commit()

    csv_content = (
        "alert_id,timestamp,entity_id,asset_id,alert_type,severity,rule_name,raw_payload,source_sensor\n"
        "ALT-001,2026-08-15T12:00:00Z,UPLOAD_CORP,SRV-01,Ransomware,CRITICAL,RansomwareRule,{},EDR-01\n"
        "ALT-002,2026-08-15T12:05:00Z,UPLOAD_CORP,SRV-02,Malware,HIGH,MalwareRule,{},EDR-02\n"
    ).encode("utf-8")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        upload_res = await client.post(
            "/api/v1/submissions/upload",
            data={"entity_id": str(entity.entity_id), "dataset_type": "alert_metadata"},
            files={"file": ("alerts.csv", io.BytesIO(csv_content), "text/csv")},
            headers=supervisor_headers,
        )
        assert upload_res.status_code == 202
        ingest_data = upload_res.json()
        assert ingest_data["total_rows"] >= 2
        assert ingest_data["status"] in ("NORMALIZED", "PARTIAL_SUCCESS")

        sub_id = ingest_data["submission_id"]

        # Check single submission
        sub_res = await client.get(f"/api/v1/submissions/{sub_id}", headers=supervisor_headers)
        assert sub_res.status_code == 200
        assert sub_res.json()["submission_id"] == sub_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_reports_export_and_benchmarks(async_db, supervisor_headers):
    """Tests compliance report export with 45/35/20 scores and peer cohort distributions."""
    app.dependency_overrides[get_db] = lambda: async_db
    transport = ASGITransport(app=app)

    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="REP_BANK",
        name="Report Bank",
        sector="Banking",
        size_tier="Tier-1",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.flush()

    score = RiskScore(
        score_id=uuid.uuid4(),
        entity_id=entity.entity_id,
        period_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 8, 31, tzinfo=timezone.utc),
        composite_risk_score=68.5,
        execution_gap_score=75.0,
        negative_space_score=60.0,
        peer_deviation_score=70.0,
        weights_applied={"execution_gap": 0.45, "negative_space": 0.35, "peer_deviation": 0.20},
        risk_tier="ELEVATED",
        trend_direction="STABLE",
        rationale_summary="Elevated risk posture.",
        calculated_at=datetime.now(timezone.utc),
    )
    async_db.add(score)
    await async_db.commit()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Report Export
        rep_res = await client.get(f"/api/v1/reports/{entity.entity_id}/export", headers=supervisor_headers)
        assert rep_res.status_code == 200
        rep_data = rep_res.json()
        assert rep_data["composite_risk_score"] == 68.5
        assert rep_data["subscores"]["execution_gap"] == 75.0
        assert rep_data["subscores"]["negative_space"] == 60.0
        assert rep_data["subscores"]["peer_deviation"] == 70.0
        assert "executive_summary" in rep_data

        # 2. Benchmarks distributions
        dist_res = await client.get("/api/v1/benchmarks/distribution", headers=supervisor_headers)
        assert dist_res.status_code == 200
        assert isinstance(dist_res.json(), list)

        # 3. Benchmarks z-scores
        z_res = await client.get("/api/v1/benchmarks/zscores", headers=supervisor_headers)
        assert z_res.status_code == 200
        assert isinstance(z_res.json(), list)

    app.dependency_overrides.clear()
