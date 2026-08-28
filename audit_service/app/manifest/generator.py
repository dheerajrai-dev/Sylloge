"""Audit manifest compilation engine."""

from datetime import datetime, timezone
import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.config import settings
from shared.errors import NotFoundError, StorageError
from shared.logging import logger
from shared.models.audit import AuditManifest
from shared.models.correlation import Correlation
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.schemas.audit import (
    AuditManifestCreate,
    AuditManifestDocument,
    AuditManifestOut,
    ManifestComponentsDTO,
)
from shared.storage.minio_client import minio_client
from ..merkle import (
    compute_manifest_merkle_tree,
    hash_findings_and_scores,
    hash_normalized_events,
    hash_quarantined_rows,
    hash_raw_submissions,
)


class AuditManifestGenerator:
    """Compiles and registers cryptographic Merkle root audit manifests."""

    @staticmethod
    async def generate_manifest_async(
        request: AuditManifestCreate,
        db: AsyncSession,
    ) -> Tuple[AuditManifestDocument, AuditManifest]:
        """Generates an audit manifest asynchronously using AsyncSession."""
        # 1. Fetch Entity
        entity_res = await db.execute(
            select(Entity).where(Entity.entity_id == request.entity_id)
        )
        entity = entity_res.scalar_one_or_none()
        if not entity:
            raise NotFoundError(f"Entity not found: {request.entity_id}")

        # 2. Fetch Raw Submissions
        sub_stmt = select(RawSubmission).where(RawSubmission.entity_id == request.entity_id)
        if request.submission_id:
            sub_stmt = sub_stmt.where(RawSubmission.submission_id == request.submission_id)
        else:
            sub_stmt = sub_stmt.where(
                RawSubmission.uploaded_at >= request.period_start,
                RawSubmission.uploaded_at <= request.period_end,
            )
        sub_res = await db.execute(sub_stmt)
        submissions = list(sub_res.scalars().all())

        # 3. Fetch Quarantined Rows
        quar_stmt = select(QuarantinedRow).where(QuarantinedRow.entity_id == request.entity_id)
        if request.submission_id:
            quar_stmt = quar_stmt.where(QuarantinedRow.submission_id == request.submission_id)
        else:
            quar_stmt = quar_stmt.where(
                QuarantinedRow.quarantined_at >= request.period_start,
                QuarantinedRow.quarantined_at <= request.period_end,
            )
        quar_res = await db.execute(quar_stmt)
        quarantined_rows = list(quar_res.scalars().all())

        # 4. Fetch Normalized Events
        evt_stmt = select(NormalizedEvent).where(NormalizedEvent.entity_id == request.entity_id)
        if request.submission_id:
            evt_stmt = evt_stmt.where(NormalizedEvent.submission_id == request.submission_id)
        else:
            evt_stmt = evt_stmt.where(
                NormalizedEvent.event_timestamp >= request.period_start,
                NormalizedEvent.event_timestamp <= request.period_end,
            )
        evt_res = await db.execute(evt_stmt)
        events = list(evt_res.scalars().all())

        # 5. Fetch Gap & Negative Space Findings, Correlations, Risk Scores
        gap_stmt = select(ExecutionGapFinding).where(
            ExecutionGapFinding.entity_id == request.entity_id,
            ExecutionGapFinding.period_start >= request.period_start,
            ExecutionGapFinding.period_end <= request.period_end,
        )
        gap_res = await db.execute(gap_stmt)
        gap_findings = list(gap_res.scalars().all())

        neg_stmt = select(NegativeSpaceFinding).where(
            NegativeSpaceFinding.entity_id == request.entity_id,
            NegativeSpaceFinding.period_start >= request.period_start,
            NegativeSpaceFinding.period_end <= request.period_end,
        )
        neg_res = await db.execute(neg_stmt)
        neg_findings = list(neg_res.scalars().all())

        corr_stmt = select(Correlation).where(Correlation.entity_id == request.entity_id)
        corr_res = await db.execute(corr_stmt)
        correlations = list(corr_res.scalars().all())

        risk_stmt = select(RiskScore).where(
            RiskScore.entity_id == request.entity_id,
            RiskScore.period_start >= request.period_start,
            RiskScore.period_end <= request.period_end,
        ).order_by(RiskScore.calculated_at.desc())
        risk_res = await db.execute(risk_stmt)
        risk_scores = list(risk_res.scalars().all())

        # 6. Compute Subtrees and Composite Root
        raw_root, raw_components = hash_raw_submissions(submissions)
        quar_root, quar_summary = hash_quarantined_rows(quarantined_rows)
        norm_root, norm_summary = hash_normalized_events(events)
        find_root, find_summary = hash_findings_and_scores(
            gap_findings, neg_findings, correlations, risk_scores
        )

        merkle_tree = compute_manifest_merkle_tree(
            raw_subtrees_sha=raw_root,
            quarantine_subtrees_sha=quar_root,
            normalized_subtrees_sha=norm_root,
            findings_subtrees_sha=find_root,
        )

        manifest_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        components = ManifestComponentsDTO(
            raw_submissions=raw_components,
            quarantine_summary=quar_summary,
            normalized_summary=norm_summary,
            findings_summary=find_summary,
        )

        manifest_doc = AuditManifestDocument(
            manifest_version="1.0.0",
            manifest_id=manifest_id,
            entity_id=request.entity_id,
            entity_code=entity.entity_code,
            period={"start": request.period_start, "end": request.period_end},
            generator_service=f"{settings.APP_NAME} audit-service v1.0.0",
            algorithm="SHA-256",
            generated_at=now,
            merkle_tree=merkle_tree,
            components=components,
        )

        # 7. Upload to MinIO
        year = now.strftime("%Y")
        month = now.strftime("%m")
        minio_path = f"{request.entity_id}/manifests/{year}/{month}/{manifest_id}_manifest.json"

        try:
            minio_client.upload_json(
                bucket_name=settings.BUCKET_AUDIT_MANIFESTS,
                object_name=minio_path,
                data=manifest_doc.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.warning(f"MinIO manifest upload skipped or failed: {exc}")

        # 8. Record in DB
        db_manifest = AuditManifest(
            manifest_id=manifest_id,
            entity_id=request.entity_id,
            submission_id=request.submission_id,
            period_start=request.period_start,
            period_end=request.period_end,
            manifest_type=request.manifest_type.value if hasattr(request.manifest_type, "value") else str(request.manifest_type),
            root_merkle_sha256=merkle_tree.root_sha256,
            file_count=len(raw_components),
            event_count=norm_summary.total_events,
            finding_count=find_summary.execution_gap_count + find_summary.negative_space_count,
            minio_manifest_path=minio_path,
            component_hashes=merkle_tree.subtrees.model_dump(),
            generated_at=now,
        )
        db.add(db_manifest)
        await db.commit()
        await db.refresh(db_manifest)

        return manifest_doc, db_manifest

    @staticmethod
    def generate_manifest_sync(
        request: AuditManifestCreate,
        db: Session,
    ) -> Tuple[AuditManifestDocument, AuditManifest]:
        """Synchronous version of generate_manifest for sync test environments."""
        entity = db.query(Entity).filter(Entity.entity_id == request.entity_id).first()
        if not entity:
            raise NotFoundError(f"Entity not found: {request.entity_id}")

        sub_q = db.query(RawSubmission).filter(RawSubmission.entity_id == request.entity_id)
        if request.submission_id:
            sub_q = sub_q.filter(RawSubmission.submission_id == request.submission_id)
        else:
            sub_q = sub_q.filter(
                RawSubmission.uploaded_at >= request.period_start,
                RawSubmission.uploaded_at <= request.period_end,
            )
        submissions = sub_q.all()

        quar_q = db.query(QuarantinedRow).filter(QuarantinedRow.entity_id == request.entity_id)
        if request.submission_id:
            quar_q = quar_q.filter(QuarantinedRow.submission_id == request.submission_id)
        else:
            quar_q = quar_q.filter(
                QuarantinedRow.quarantined_at >= request.period_start,
                QuarantinedRow.quarantined_at <= request.period_end,
            )
        quarantined_rows = quar_q.all()

        evt_q = db.query(NormalizedEvent).filter(NormalizedEvent.entity_id == request.entity_id)
        if request.submission_id:
            evt_q = evt_q.filter(NormalizedEvent.submission_id == request.submission_id)
        else:
            evt_q = evt_q.filter(
                NormalizedEvent.event_timestamp >= request.period_start,
                NormalizedEvent.event_timestamp <= request.period_end,
            )
        events = evt_q.all()

        gap_findings = db.query(ExecutionGapFinding).filter(
            ExecutionGapFinding.entity_id == request.entity_id,
            ExecutionGapFinding.period_start >= request.period_start,
            ExecutionGapFinding.period_end <= request.period_end,
        ).all()

        neg_findings = db.query(NegativeSpaceFinding).filter(
            NegativeSpaceFinding.entity_id == request.entity_id,
            NegativeSpaceFinding.period_start >= request.period_start,
            NegativeSpaceFinding.period_end <= request.period_end,
        ).all()

        correlations = db.query(Correlation).filter(Correlation.entity_id == request.entity_id).all()
        risk_scores = db.query(RiskScore).filter(
            RiskScore.entity_id == request.entity_id,
            RiskScore.period_start >= request.period_start,
            RiskScore.period_end <= request.period_end,
        ).order_by(RiskScore.calculated_at.desc()).all()

        raw_root, raw_components = hash_raw_submissions(submissions)
        quar_root, quar_summary = hash_quarantined_rows(quarantined_rows)
        norm_root, norm_summary = hash_normalized_events(events)
        find_root, find_summary = hash_findings_and_scores(
            gap_findings, neg_findings, correlations, risk_scores
        )

        merkle_tree = compute_manifest_merkle_tree(
            raw_subtrees_sha=raw_root,
            quarantine_subtrees_sha=quar_root,
            normalized_subtrees_sha=norm_root,
            findings_subtrees_sha=find_root,
        )

        manifest_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        components = ManifestComponentsDTO(
            raw_submissions=raw_components,
            quarantine_summary=quar_summary,
            normalized_summary=norm_summary,
            findings_summary=find_summary,
        )

        manifest_doc = AuditManifestDocument(
            manifest_version="1.0.0",
            manifest_id=manifest_id,
            entity_id=request.entity_id,
            entity_code=entity.entity_code,
            period={"start": request.period_start, "end": request.period_end},
            generator_service=f"{settings.APP_NAME} audit-service v1.0.0",
            algorithm="SHA-256",
            generated_at=now,
            merkle_tree=merkle_tree,
            components=components,
        )

        year = now.strftime("%Y")
        month = now.strftime("%m")
        minio_path = f"{request.entity_id}/manifests/{year}/{month}/{manifest_id}_manifest.json"

        try:
            minio_client.upload_json(
                bucket_name=settings.BUCKET_AUDIT_MANIFESTS,
                object_name=minio_path,
                data=manifest_doc.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.warning(f"MinIO manifest upload skipped or failed: {exc}")

        db_manifest = AuditManifest(
            manifest_id=manifest_id,
            entity_id=request.entity_id,
            submission_id=request.submission_id,
            period_start=request.period_start,
            period_end=request.period_end,
            manifest_type=request.manifest_type.value if hasattr(request.manifest_type, "value") else str(request.manifest_type),
            root_merkle_sha256=merkle_tree.root_sha256,
            file_count=len(raw_components),
            event_count=norm_summary.total_events,
            finding_count=find_summary.execution_gap_count + find_summary.negative_space_count,
            minio_manifest_path=minio_path,
            component_hashes=merkle_tree.subtrees.model_dump(),
            generated_at=now,
        )
        db.add(db_manifest)
        db.commit()
        db.refresh(db_manifest)

        return manifest_doc, db_manifest
