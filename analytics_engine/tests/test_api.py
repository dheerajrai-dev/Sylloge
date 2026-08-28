"""Integration and API tests for the Analytics Engine FastAPI microservice."""

from datetime import datetime, timedelta, timezone
from typing import Dict
import uuid
from httpx import ASGITransport, AsyncClient
import pytest

from analytics_engine.main import app
from shared.db.session import get_db


@pytest.mark.asyncio
async def test_healthcheck():
    """Verifies GET /health returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "analytics-engine"


@pytest.mark.asyncio
async def test_rules_api(auth_headers: Dict[str, str]):
    """Verifies listing and registering rules via /api/v1/analytics/rules."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. List rules
        resp = await client.get("/api/v1/analytics/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["execution_gap_rules"]) >= 8
        assert len(data["negative_space_checks"]) >= 8

        # 2. Register custom execution gap rule
        custom_rule = {
            "rule_code": "EG-CUSTOM-01",
            "name": "Custom Critical Alert Check",
            "category": "TRIAGE",
            "target_dataset": "alert_metadata",
            "severity_base": 80,
            "confidence": 0.90,
            "description_template": "Custom gap detected for {ref_id}",
            "rationale_template": "Custom rationale for {ref_id}",
            "is_active": True,
        }
        create_resp = await client.post(
            "/api/v1/analytics/rules/execution-gap",
            json=custom_rule,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        created_data = create_resp.json()
        assert created_data["rule_code"] == "EG-CUSTOM-01"

        # 3. Toggle status
        toggle_resp = await client.patch(
            "/api/v1/analytics/rules/EG-CUSTOM-01/status",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_analyze_endpoint(auth_headers: Dict[str, str], entity_id: uuid.UUID, sample_now: datetime, async_db):
    """Verifies POST /api/v1/analytics/analyze executes full pipeline."""
    # Override get_db_session dependency to use test async_db
    app.dependency_overrides[get_db] = lambda: async_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create sample events payload
        events = [
            {
                "event_id": str(uuid.uuid4()),
                "submission_id": str(uuid.uuid4()),
                "entity_id": str(entity_id),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "raw_ref_id": "ALT-TEST-001",
                "severity": "CRITICAL",
                "asset_id": "SRV-TEST-01",
                "event_timestamp": (sample_now - timedelta(hours=3)).isoformat(),
                "raw_row_index": 1,
            },
            {
                "event_id": str(uuid.uuid4()),
                "submission_id": str(uuid.uuid4()),
                "entity_id": str(entity_id),
                "dataset_type": "case_management",
                "standard_event_type": "CASE",
                "raw_ref_id": "CASE-TEST-001",
                "status": "OPEN",
                "priority": "P1_CRITICAL",
                "severity": "CRITICAL",
                "event_timestamp": (sample_now - timedelta(hours=5)).isoformat(),
                "raw_row_index": 2,
            },
        ]

        payload = {
            "entity_id": str(entity_id),
            "period_start": (sample_now - timedelta(days=1)).isoformat(),
            "period_end": sample_now.isoformat(),
            "sector": "Banking",
            "size_tier": "Tier-1",
            "events": events,
            "persist_to_db": True,
        }

        resp = await client.post("/api/v1/analytics/analyze", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["entity_id"] == str(entity_id)
        assert data["execution_gap_count"] >= 1
        assert "risk_score" in data
        assert 0.0 <= data["risk_score"]["composite_risk_score"] <= 100.0
        assert len(data["rationale_cards"]) >= 1

        # 4. Verify querying findings
        eg_resp = await client.get(f"/api/v1/analytics/findings/execution-gap?entity_id={entity_id}")
        assert eg_resp.status_code == 200
        eg_findings = eg_resp.json()
        assert len(eg_findings) >= 1

        # 5. Verify querying risk scores
        scores_resp = await client.get(f"/api/v1/analytics/scores/{entity_id}")
        assert scores_resp.status_code == 200
        scores = scores_resp.json()
        assert len(scores) >= 1
        assert scores[0]["composite_risk_score"] == data["risk_score"]["composite_risk_score"]

    app.dependency_overrides.clear()
