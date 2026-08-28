"""Audit manifest cryptographic verification engine."""

from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.errors import NotFoundError
from shared.models.audit import AuditManifest
from shared.models.correlation import Correlation
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.schemas.audit import AuditVerificationResult
from ..merkle import (
    compute_manifest_merkle_tree,
    hash_findings_and_scores,
    hash_normalized_events,
    hash_quarantined_rows,
    hash_raw_submissions,
)


class AuditManifestVerifier:
    """Verifies cryptographic integrity of audit manifests against current database state."""

    @staticmethod
    async def verify_manifest_async(
        manifest_id: uuid.UUID,
        db: AsyncSession,
    ) -> AuditVerificationResult:
        """Asynchronously verifies the Merkle root of an audit manifest."""
        manifest_res = await db.execute(
            select(AuditManifest).where(AuditManifest.manifest_id == manifest_id)
        )
        db_manifest = manifest_res.scalar_one_or_none()
        if not db_manifest:
            raise NotFoundError(f"Audit manifest not found: {manifest_id}")

        entity_id = db_manifest.entity_id
        submission_id = db_manifest.submission_id
        period_start = db_manifest.period_start
        period_end = db_manifest.period_end

        # Re-fetch Submissions
        sub_stmt = select(RawSubmission).where(RawSubmission.entity_id == entity_id)
        if submission_id:
            sub_stmt = sub_stmt.where(RawSubmission.submission_id == submission_id)
        else:
            sub_stmt = sub_stmt.where(
                RawSubmission.uploaded_at >= period_start,
                RawSubmission.uploaded_at <= period_end,
            )
        sub_res = await db.execute(sub_stmt)
        submissions = list(sub_res.scalars().all())

        # Re-fetch Quarantined Rows
        quar_stmt = select(QuarantinedRow).where(QuarantinedRow.entity_id == entity_id)
        if submission_id:
            quar_stmt = quar_stmt.where(QuarantinedRow.submission_id == submission_id)
        else:
            quar_stmt = quar_stmt.where(
                QuarantinedRow.quarantined_at >= period_start,
                QuarantinedRow.quarantined_at <= period_end,
            )
        quar_res = await db.execute(quar_stmt)
        quarantined_rows = list(quar_res.scalars().all())

        # Re-fetch Normalized Events
        evt_stmt = select(NormalizedEvent).where(NormalizedEvent.entity_id == entity_id)
        if submission_id:
            evt_stmt = evt_stmt.where(NormalizedEvent.submission_id == submission_id)
        else:
            evt_stmt = evt_stmt.where(
                NormalizedEvent.event_timestamp >= period_start,
                NormalizedEvent.event_timestamp <= period_end,
            )
        evt_res = await db.execute(evt_stmt)
        events = list(evt_res.scalars().all())

        # Re-fetch Findings, Correlations, Risk Scores
        gap_stmt = select(ExecutionGapFinding).where(
            ExecutionGapFinding.entity_id == entity_id,
            ExecutionGapFinding.period_start >= period_start,
            ExecutionGapFinding.period_end <= period_end,
        )
        gap_res = await db.execute(gap_stmt)
        gap_findings = list(gap_res.scalars().all())

        neg_stmt = select(NegativeSpaceFinding).where(
            NegativeSpaceFinding.entity_id == entity_id,
            NegativeSpaceFinding.period_start >= period_start,
            NegativeSpaceFinding.period_end <= period_end,
        )
        neg_res = await db.execute(neg_stmt)
        neg_findings = list(neg_res.scalars().all())

        corr_stmt = select(Correlation).where(Correlation.entity_id == entity_id)
        corr_res = await db.execute(corr_stmt)
        correlations = list(corr_res.scalars().all())

        risk_stmt = select(RiskScore).where(
            RiskScore.entity_id == entity_id,
            RiskScore.period_start >= period_start,
            RiskScore.period_end <= period_end,
        ).order_by(RiskScore.calculated_at.desc())
        risk_res = await db.execute(risk_stmt)
        risk_scores = list(risk_res.scalars().all())

        # Recompute Subtrees
        raw_root, _ = hash_raw_submissions(submissions)
        quar_root, _ = hash_quarantined_rows(quarantined_rows)
        norm_root, _ = hash_normalized_events(events)
        find_root, _ = hash_findings_and_scores(
            gap_findings, neg_findings, correlations, risk_scores
        )

        merkle_tree = compute_manifest_merkle_tree(
            raw_subtrees_sha=raw_root,
            quarantine_subtrees_sha=quar_root,
            normalized_subtrees_sha=norm_root,
            findings_subtrees_sha=find_root,
        )

        recomputed_root = merkle_tree.root_sha256
        stored_root = db_manifest.root_merkle_sha256
        stored_hashes = db_manifest.component_hashes or {}

        discrepancies: List[str] = []
        if stored_hashes.get("raw_submissions_sha256") != raw_root:
            discrepancies.append(
                f"Raw submissions subtree mismatch: stored={stored_hashes.get('raw_submissions_sha256')}, recomputed={raw_root}"
            )
        if stored_hashes.get("quarantined_records_sha256") != quar_root:
            discrepancies.append(
                f"Quarantined records subtree mismatch: stored={stored_hashes.get('quarantined_records_sha256')}, recomputed={quar_root}"
            )
        if stored_hashes.get("normalized_events_sha256") != norm_root:
            discrepancies.append(
                f"Normalized events subtree mismatch: stored={stored_hashes.get('normalized_events_sha256')}, recomputed={norm_root}"
            )
        if stored_hashes.get("findings_and_scores_sha256") != find_root:
            discrepancies.append(
                f"Findings and scores subtree mismatch: stored={stored_hashes.get('findings_and_scores_sha256')}, recomputed={find_root}"
            )
        if stored_root != recomputed_root:
            discrepancies.append(
                f"Root Merkle hash mismatch: stored={stored_root}, recomputed={recomputed_root}"
            )

        is_valid = len(discrepancies) == 0
        return AuditVerificationResult(
            manifest_id=manifest_id,
            entity_id=entity_id,
            is_valid=is_valid,
            status="VERIFIED" if is_valid else "TAMPER_DETECTED",
            stored_root_sha256=stored_root,
            recomputed_root_sha256=recomputed_root,
            discrepancies=discrepancies,
            verified_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def verify_manifest_sync(
        manifest_id: uuid.UUID,
        db: Session,
    ) -> AuditVerificationResult:
        """Synchronous version of manifest verification."""
        db_manifest = db.query(AuditManifest).filter(AuditManifest.manifest_id == manifest_id).first()
        if not db_manifest:
            raise NotFoundError(f"Audit manifest not found: {manifest_id}")

        entity_id = db_manifest.entity_id
        submission_id = db_manifest.submission_id
        period_start = db_manifest.period_start
        period_end = db_manifest.period_end

        sub_q = db.query(RawSubmission).filter(RawSubmission.entity_id == entity_id)
        if submission_id:
            sub_q = sub_q.filter(RawSubmission.submission_id == submission_id)
        else:
            sub_q = sub_q.filter(
                RawSubmission.uploaded_at >= period_start,
                RawSubmission.uploaded_at <= period_end,
            )
        submissions = sub_q.all()

        quar_q = db.query(QuarantinedRow).filter(QuarantinedRow.entity_id == entity_id)
        if submission_id:
            quar_q = quar_q.filter(QuarantinedRow.submission_id == submission_id)
        else:
            quar_q = quar_q.filter(
                QuarantinedRow.quarantined_at >= period_start,
                QuarantinedRow.quarantined_at <= period_end,
            )
        quarantined_rows = quar_q.all()

        evt_q = db.query(NormalizedEvent).filter(NormalizedEvent.entity_id == entity_id)
        if submission_id:
            evt_q = evt_q.filter(NormalizedEvent.submission_id == submission_id)
        else:
            evt_q = evt_q.filter(
                NormalizedEvent.event_timestamp >= period_start,
                NormalizedEvent.event_timestamp <= period_end,
            )
        events = evt_q.all()

        gap_findings = db.query(ExecutionGapFinding).filter(
            ExecutionGapFinding.entity_id == entity_id,
            ExecutionGapFinding.period_start >= period_start,
            ExecutionGapFinding.period_end <= period_end,
        ).all()

        neg_findings = db.query(NegativeSpaceFinding).filter(
            NegativeSpaceFinding.entity_id == entity_id,
            NegativeSpaceFinding.period_start >= period_start,
            NegativeSpaceFinding.period_end <= period_end,
        ).all()

        correlations = db.query(Correlation).filter(Correlation.entity_id == entity_id).all()
        risk_scores = db.query(RiskScore).filter(
            RiskScore.entity_id == entity_id,
            RiskScore.period_start >= period_start,
            RiskScore.period_end <= period_end,
        ).order_by(RiskScore.calculated_at.desc()).all()

        raw_root, _ = hash_raw_submissions(submissions)
        quar_root, _ = hash_quarantined_rows(quarantined_rows)
        norm_root, _ = hash_normalized_events(events)
        find_root, _ = hash_findings_and_scores(
            gap_findings, neg_findings, correlations, risk_scores
        )

        merkle_tree = compute_manifest_merkle_tree(
            raw_subtrees_sha=raw_root,
            quarantine_subtrees_sha=quar_root,
            normalized_subtrees_sha=norm_root,
            findings_subtrees_sha=find_root,
        )

        recomputed_root = merkle_tree.root_sha256
        stored_root = db_manifest.root_merkle_sha256
        stored_hashes = db_manifest.component_hashes or {}

        discrepancies: List[str] = []
        if stored_hashes.get("raw_submissions_sha256") != raw_root:
            discrepancies.append(
                f"Raw submissions subtree mismatch: stored={stored_hashes.get('raw_submissions_sha256')}, recomputed={raw_root}"
            )
        if stored_hashes.get("quarantined_records_sha256") != quar_root:
            discrepancies.append(
                f"Quarantined records subtree mismatch: stored={stored_hashes.get('quarantined_records_sha256')}, recomputed={quar_root}"
            )
        if stored_hashes.get("normalized_events_sha256") != norm_root:
            discrepancies.append(
                f"Normalized events subtree mismatch: stored={stored_hashes.get('normalized_events_sha256')}, recomputed={norm_root}"
            )
        if stored_hashes.get("findings_and_scores_sha256") != find_root:
            discrepancies.append(
                f"Findings and scores subtree mismatch: stored={stored_hashes.get('findings_and_scores_sha256')}, recomputed={find_root}"
            )
        if stored_root != recomputed_root:
            discrepancies.append(
                f"Root Merkle hash mismatch: stored={stored_root}, recomputed={recomputed_root}"
            )

        is_valid = len(discrepancies) == 0
        return AuditVerificationResult(
            manifest_id=manifest_id,
            entity_id=entity_id,
            is_valid=is_valid,
            status="VERIFIED" if is_valid else "TAMPER_DETECTED",
            stored_root_sha256=stored_root,
            recomputed_root_sha256=recomputed_root,
            discrepancies=discrepancies,
            verified_at=datetime.now(timezone.utc),
        )
