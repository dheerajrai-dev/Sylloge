"""FastAPI endpoint integration tests for data-processing microservice."""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.event import NormalizedEvent
from shared.models.quarantine import QuarantinedRow
from shared.models.submission import RawSubmission


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Verifies /health endpoint returns 200 and healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "data-processing"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_trigger_ingest_endpoint_clean_csv(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_test_entity,
    sample_test_submission,
):
    """Tests /api/v1/process/ingest with valid CSV content."""
    csv_payload = (
        "alert_id,timestamp,severity,rule_name,source_ip,destination_ip,asset_id\n"
        "ALT-001,2026-08-25T10:00:00Z,CRITICAL,SQL_Injection,1.2.3.4,10.0.0.5,DB-01\n"
        "ALT-002,2026-08-25T10:05:00Z,HIGH,XSS_Attempt,1.2.3.5,10.0.0.6,WEB-01\n"
    )

    request_data = {
        "submission_id": str(sample_test_submission.submission_id),
        "entity_id": str(sample_test_entity.entity_id),
        "dataset_type": "alert_metadata",
        "raw_content": csv_payload,
    }

    response = await client.post("/api/v1/process/ingest", json=request_data)
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["status"] == "NORMALIZED"
    assert res_json["total_rows"] == 2
    assert res_json["valid_rows"] == 2
    assert res_json["quarantined_rows"] == 0

    # Verify NormalizedEvent stored in DB
    stmt = select(NormalizedEvent).where(NormalizedEvent.submission_id == sample_test_submission.submission_id)
    events = (await db_session.execute(stmt)).scalars().all()
    assert len(events) == 2
    assert events[0].raw_ref_id == "ALT-001"
    assert events[0].severity == "CRITICAL"


@pytest.mark.asyncio
async def test_trigger_ingest_endpoint_with_quarantine(
    client: AsyncClient,
    db_session: AsyncSession,
    sample_test_entity,
    sample_test_submission,
):
    """Tests /api/v1/process/ingest with mixed valid and invalid rows, asserting row-level quarantine."""
    mixed_csv = (
        "alert_id,timestamp,severity,rule_name\n"
        "ALT-101,2026-08-25T12:00:00Z,HIGH,ValidRule\n"
        ",2026-08-25T12:05:00Z,HIGH,MissingAlertId\n"
        "ALT-103,INVALID_DATE,LOW,BadDate\n"
    )

    request_data = {
        "submission_id": str(sample_test_submission.submission_id),
        "entity_id": str(sample_test_entity.entity_id),
        "dataset_type": "alert_metadata",
        "raw_content": mixed_csv,
    }

    response = await client.post("/api/v1/process/ingest", json=request_data)
    assert response.status_code == 200
    res_json = response.json()

    assert res_json["status"] == "PARTIAL_SUCCESS"
    assert res_json["total_rows"] == 3
    assert res_json["valid_rows"] == 1
    assert res_json["quarantined_rows"] == 2

    # Verify database state
    q_stmt = select(QuarantinedRow).where(QuarantinedRow.submission_id == sample_test_submission.submission_id)
    q_rows = (await db_session.execute(q_stmt)).scalars().all()
    assert len(q_rows) == 2

    e_stmt = select(NormalizedEvent).where(NormalizedEvent.submission_id == sample_test_submission.submission_id)
    e_rows = (await db_session.execute(e_stmt)).scalars().all()
    assert len(e_rows) == 1
    assert e_rows[0].raw_ref_id == "ALT-101"

    # Verify Quarantine inspection endpoints
    q_resp = await client.get(f"/api/v1/process/quarantine/{sample_test_submission.submission_id}")
    assert q_resp.status_code == 200
    assert len(q_resp.json()) == 2

    summary_resp = await client.get(f"/api/v1/process/quarantine/{sample_test_submission.submission_id}/summary")
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_quarantined"] == 2


@pytest.mark.asyncio
async def test_normalize_direct_endpoint(client: AsyncClient, sample_test_entity):
    """Tests /api/v1/process/normalize on-demand endpoint."""
    records = [
        {"alert_id": "A-1", "timestamp": "2026-08-25T08:00:00Z", "rule_name": "SSH_Brute", "severity": "HIGH"},
        {"alert_id": "A-2", "timestamp": "2026-08-25T08:05:00Z", "rule_name": "RDP_Brute", "severity": "CRITICAL"},
    ]
    payload = {
        "entity_id": str(sample_test_entity.entity_id),
        "dataset_type": "alert_metadata",
        "records": records,
    }

    response = await client.post("/api/v1/process/normalize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 2
    assert len(data["normalized_records"]) == 2
    assert data["normalized_records"][0]["raw_ref_id"] == "A-1"
    assert data["normalized_records"][0]["standard_event_type"] == "ALERT"


@pytest.mark.asyncio
async def test_mapping_profiles_crud_endpoint(client: AsyncClient, sample_test_entity):
    """Tests registering and retrieving field mapping profiles."""
    payload = {
        "entity_id": str(sample_test_entity.entity_id),
        "dataset_type": "alert_metadata",
        "version": 1,
        "mapping_rules": {
            "CustomID": "raw_ref_id",
            "EventTimestamp": "event_timestamp",
        },
        "transform_rules": {
            "timestamp": {"format": "%Y-%m-%d %H:%M:%S"},
        },
        "is_active": True,
    }

    create_resp = await client.post("/api/v1/process/mapping-profiles", json=payload)
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    assert created_data["mapping_rules"]["CustomID"] == "raw_ref_id"

    # Get active profile
    get_resp = await client.get(f"/api/v1/process/mapping-profiles/{sample_test_entity.entity_id}/alert_metadata")
    assert get_resp.status_code == 200
    fetched_data = get_resp.json()
    assert fetched_data["profile_id"] == created_data["profile_id"]
