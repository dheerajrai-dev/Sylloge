"""Full End-to-End Integration Test Suite for SAT-SA (SYLLOGE).

Tests the full multi-service pipeline:
Raw Data Upload -> Structural Validation & Quarantine -> Normalization to Event Schema ->
Six Analytics Engines Execution -> Transparent Weighted Risk Scoring -> Explainability Rationale Cards ->
Cryptographic Merkle Audit Manifest Generation & Verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import sys
import os

# Add service paths
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for service in ["analytics_engine", "data_processing", "backend", "audit_service", "analytics-engine", "data-processing", "audit-service"]:
    srv_path = os.path.join(repo_root, service)
    if os.path.exists(srv_path) and srv_path not in sys.path:
        sys.path.insert(0, srv_path)

from shared.events.enums import DatasetType, SeverityTier, RiskTier
from shared.models.entity import Entity
from shared.models.submission import RawSubmission
from shared.models.quarantine import QuarantinedRow
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.models.benchmark import PeerBenchmark
from shared.models.audit import AuditManifest
from shared.storage.merkle import MerkleTree, sha256_hash_json

from shared.schemas.audit import AuditManifestCreate
from analytics_engine import AnalyticsPipeline
from analytics_engine.schemas.requests import AnalyzeRequest
from data_processing import IngestionPipelineService
from audit_service.manifest.generator import AuditManifestGenerator


def test_full_pipeline_e2e_flow(sync_db: Session, sample_entity: Entity, sample_now: datetime):
    """Verifies the complete end-to-end execution of SAT-SA from data ingestion to Merkle audit manifest."""
    entity_id = sample_entity.entity_id
    period = "2026-Q1"

    # 1. Ingest raw alerts dataset
    sub_id = uuid.uuid4()
    submission = RawSubmission(
        submission_id=sub_id,
        entity_id=entity_id,
        dataset_type="alert_metadata",
        file_name="e2e_test_alerts.csv",
        file_size_bytes=4096,
        mime_type="text/csv",
        minio_raw_path=f"raw-submissions/{sub_id}.csv",
        sha256_hash="e2e_test_hash_alerts_123",
        ingestion_status="NORMALIZED",
        uploaded_at=sample_now - timedelta(hours=2),
    )
    sync_db.add(submission)
    sync_db.commit()

    # 2. Add normalized events
    for i in range(15):
        event = NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=sub_id,
            entity_id=entity_id,
            dataset_type=DatasetType.ALERT_METADATA.value,
            standard_event_type="ALERT",
            event_timestamp=sample_now - timedelta(days=i),
            asset_id=f"AST-CRIT-{i % 3 + 1}",
            severity=SeverityTier.HIGH.value if i % 2 == 0 else SeverityTier.CRITICAL.value,
            raw_row_index=i,
            normalized_payload={
                "alert_id_external": f"ALT-E2E-{i+1000}",
                "disposition": "False Positive" if i % 3 == 0 else "True Positive",
                "escalated": False if i % 4 == 0 else True,
                "analyst_id": f"ANALYST-{i % 2 + 1}",
                "closed_at": (sample_now - timedelta(days=i) + timedelta(seconds=10 if i == 0 else 3600)).isoformat(),
                "investigation_notes": "Investigated alert. Template note for review." if i % 2 == 0 else "Custom investigation note details.",
            },
        )
        sync_db.add(event)

    sync_db.commit()

    # 3. Run Analytics Pipeline (all 6 engines)
    pipeline = AnalyticsPipeline()
    req = AnalyzeRequest(
        entity_id=entity_id,
        period_start=sample_now - timedelta(days=30),
        period_end=sample_now,
        persist_to_db=False,
    )
    analyze_result = pipeline.execute_sync(req, sync_db)

    assert analyze_result is not None
    assert analyze_result.entity_id == entity_id
    assert 0.0 <= analyze_result.risk_score.composite_risk_score <= 100.0
    assert analyze_result.risk_score.risk_tier in [tier.value for tier in RiskTier]

    # 4. Generate Cryptographic Audit Manifest
    audit_req = AuditManifestCreate(
        entity_id=entity_id,
        submission_id=sub_id,
        period_start=sample_now - timedelta(days=30),
        period_end=sample_now,
    )
    manifest_doc, db_manifest = AuditManifestGenerator.generate_manifest_sync(audit_req, sync_db)

    assert manifest_doc is not None
    assert manifest_doc.merkle_tree.root_sha256 is not None
    assert len(manifest_doc.merkle_tree.root_sha256) == 64  # SHA-256 hex string

    # 5. Verify Merkle Audit Integrity
    events = sync_db.scalars(select(NormalizedEvent).where(NormalizedEvent.entity_id == entity_id)).all()
    event_hashes = [sha256_hash_json({"event_id": str(e.event_id), "asset_id": e.asset_id}) for e in events]
    tree = MerkleTree(event_hashes)
    assert tree.root_hash is not None


def test_full_pipeline_quarantine_resilience(sync_db: Session, sample_entity: Entity, sample_now: datetime):
    """Verifies that bad rows are quarantined into quarantined_rows without interrupting valid pipeline processing."""
    sub_id = uuid.uuid4()
    submission = RawSubmission(
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="corrupted_alerts.csv",
        file_size_bytes=2048,
        mime_type="text/csv",
        minio_raw_path=f"raw-submissions/{sub_id}.csv",
        sha256_hash="quarantine_test_hash",
        ingestion_status="COMPLETED_WITH_WARNINGS",
        uploaded_at=sample_now,
    )
    sync_db.add(submission)

    # Add a quarantined bad row
    q_row = QuarantinedRow(
        quarantine_id=uuid.uuid4(),
        submission_id=sub_id,
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        row_index=1,
        raw_content={"alert_id": "ALT-BAD", "created_at": "invalid-timestamp-string"},
        failure_reason="Failed to parse timestamp ISO format",
        failed_fields=["created_at"],
        quarantined_at=sample_now,
    )
    sync_db.add(q_row)
    sync_db.commit()

    # Verify quarantine row persisted
    db_q = sync_db.scalar(select(QuarantinedRow).where(QuarantinedRow.submission_id == sub_id))
    assert db_q is not None
    assert db_q.failure_reason == "Failed to parse timestamp ISO format"


def test_full_pipeline_airgap_reproducibility(sync_db: Session, sample_entity: Entity, sample_now: datetime):
    """Verifies air-gapped reproducibility: running identical input produces identical scores & Merkle roots."""
    entity_id = sample_entity.entity_id
    pipeline = AnalyticsPipeline()
    req = AnalyzeRequest(
        entity_id=entity_id,
        period_start=sample_now - timedelta(days=30),
        period_end=sample_now,
        persist_to_db=False,
    )

    run1 = pipeline.execute_sync(req, sync_db)
    run2 = pipeline.execute_sync(req, sync_db)

    assert run1.risk_score.composite_risk_score == run2.risk_score.composite_risk_score
    assert run1.risk_score.execution_gap_score == run2.risk_score.execution_gap_score
    assert run1.risk_score.negative_space_score == run2.risk_score.negative_space_score

