"""Top-level Integration & End-to-End Tests for Milestone 3 (Six-Engine Analytics Core)."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import sys
import os
ae_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analytics_engine")
if ae_root not in sys.path:
    sys.path.insert(0, ae_root)

from analytics_engine import (
    AnalyticsPipeline,
    CorrelationEngine,
    ExecutionGapEngine,
    ExplainabilityEngine,
    NegativeSpaceEngine,
    PeerBenchmarkEngine,
    RiskScoringEngine,
)
from shared.events.enums import DatasetType, SeverityTier
from shared.models.benchmark import PeerBenchmark
from shared.models.correlation import Correlation
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from analytics_engine.schemas.requests import AnalyzeRequest


def test_e2e_sync_pipeline_all_engines(sync_db: Session, sample_entity: Entity, sample_now: datetime):
    """Verifies end-to-end synchronous execution of all 6 engines with DB persistence."""
    # 1. Create a dummy submission
    sub_id = uuid.uuid4()
    submission = RawSubmission(
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="e2e_alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path=f"raw-submissions/{sub_id}.csv",
        sha256_hash="e2e_hash",
        ingestion_status="NORMALIZED",
    )
    sync_db.add(submission)
    sync_db.commit()

    # 2. Add realistic normalized events covering multiple datasets
    events_data = [
        # Alert 1: Critical alert uninvestigated (triggers EG-01)
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="alert_metadata",
            standard_event_type="ALERT",
            event_timestamp=sample_now - timedelta(hours=4),
            asset_id="SRV-PROD-01",
            severity="CRITICAL",
            action="Ransomware Detection",
            raw_ref_id="ALT-E2E-001",
            raw_row_index=1,
            normalized_payload={"delay_hours": 4.0},
        ),
        # Alert 2: Repeat alert on same asset within 24h
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="alert_metadata",
            standard_event_type="ALERT",
            event_timestamp=sample_now - timedelta(hours=3),
            asset_id="SRV-PROD-01",
            severity="CRITICAL",
            action="Ransomware Detection",
            raw_ref_id="ALT-E2E-002",
            raw_row_index=2,
        ),
        # Alert 3: Another repeat alert on same asset (3 Criticals in 24h triggers burst cluster)
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="alert_metadata",
            standard_event_type="ALERT",
            event_timestamp=sample_now - timedelta(hours=2),
            asset_id="SRV-PROD-01",
            severity="CRITICAL",
            action="Ransomware Detection",
            raw_ref_id="ALT-E2E-003",
            raw_row_index=3,
        ),
        # Case 1: P1 Critical case open > 4 hours without escalation (triggers EG-02)
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="case_management",
            standard_event_type="CASE",
            event_timestamp=sample_now - timedelta(hours=8),
            status="OPEN",
            severity="CRITICAL",
            raw_ref_id="CASE-E2E-001",
            raw_row_index=4,
            normalized_payload={"priority": "P1_CRITICAL"},
        ),
        # Investigation 1 & 2: Identical notes across distinct cases (triggers note clone correlation)
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="investigation_records",
            standard_event_type="INVESTIGATION",
            event_timestamp=sample_now - timedelta(hours=1),
            raw_ref_id="INV-E2E-001",
            raw_row_index=5,
            normalized_payload={
                "case_id": "CASE-101",
                "investigation_notes": "Standard false positive triage. User verified traveling. Active Directory session valid.",
            },
        ),
        NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=sample_entity.entity_id,
            dataset_type="investigation_records",
            standard_event_type="INVESTIGATION",
            event_timestamp=sample_now - timedelta(minutes=45),
            raw_ref_id="INV-E2E-002",
            raw_row_index=6,
            normalized_payload={
                "case_id": "CASE-102",
                "investigation_notes": "Standard false positive triage. User verified traveling. Active Directory session valid.",
            },
        ),
    ]

    for ev in events_data:
        sync_db.add(ev)
    sync_db.commit()

    # 3. Execute Master Pipeline
    pipeline = AnalyticsPipeline()
    req = AnalyzeRequest(
        entity_id=sample_entity.entity_id,
        period_start=sample_now - timedelta(days=1),
        period_end=sample_now,
        sector="Banking",
        size_tier="Tier-1",
        persist_to_db=True,
    )

    response = pipeline.execute_sync(request=req, sync_session=sync_db)

    # 4. Verify Consolidated Results
    assert response.entity_id == sample_entity.entity_id
    assert response.execution_gap_count >= 2  # EG-01, EG-02
    assert response.correlations_count >= 1  # Note clone or repeat burst
    assert 0.0 <= response.risk_score.composite_risk_score <= 100.0
    assert len(response.rationale_cards) >= 2
    assert len(response.benchmarks) == 5

    # 5. Verify Database Records Persisted Correctly
    persisted_gaps = sync_db.query(ExecutionGapFinding).filter(ExecutionGapFinding.entity_id == sample_entity.entity_id).all()
    assert len(persisted_gaps) >= 2

    persisted_scores = sync_db.query(RiskScore).filter(RiskScore.entity_id == sample_entity.entity_id).all()
    assert len(persisted_scores) == 1
    assert persisted_scores[0].composite_risk_score == response.risk_score.composite_risk_score

    persisted_benchmarks = sync_db.query(PeerBenchmark).all()
    assert len(persisted_benchmarks) >= 5


@pytest.mark.asyncio
async def test_e2e_async_pipeline(async_db: AsyncSession, sample_now: datetime):
    """Verifies end-to-end asynchronous pipeline with database session."""
    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code="TELECOM_BETA",
        name="Telecom Beta",
        sector="Telecom",
        size_tier="Tier-2",
        is_active=True,
    )
    async_db.add(entity)
    await async_db.commit()

    pipeline = AnalyticsPipeline()
    events = [
        {
            "event_id": str(uuid.uuid4()),
            "submission_id": str(uuid.uuid4()),
            "entity_id": str(entity.entity_id),
            "dataset_type": "alert_metadata",
            "standard_event_type": "ALERT",
            "raw_ref_id": "ALT-TEL-01",
            "severity": "CRITICAL",
            "event_timestamp": (sample_now - timedelta(hours=5)).isoformat(),
            "raw_row_index": 1,
        }
    ]

    req = AnalyzeRequest(
        entity_id=entity.entity_id,
        period_start=sample_now - timedelta(days=1),
        period_end=sample_now,
        sector="Telecom",
        size_tier="Tier-2",
        events=events,
        persist_to_db=True,
    )

    response = await pipeline.execute_async(request=req, db_session=async_db)
    assert response.entity_id == entity.entity_id
    assert response.execution_gap_count >= 1
    assert response.risk_score.composite_risk_score > 0.0
    assert len(response.rationale_cards) >= 1

    # Verify DB records in async session
    stmt = select(RiskScore).where(RiskScore.entity_id == entity.entity_id)
    scores = (await async_db.execute(stmt)).scalars().all()
    assert len(scores) == 1
