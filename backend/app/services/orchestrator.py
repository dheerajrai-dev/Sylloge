"""Pipeline Orchestrator for SAT-SA Full Analytics & Audit Lifecycle."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import logger
from shared.models.entity import Entity
from shared.models.risk_score import RiskScore
from .clients import AnalyticsEngineClient, AuditServiceClient, DataProcessingClient


class PipelineOrchestrator:
    """Orchestrates end-to-end processing across ingestion, analytics, scoring, and audit."""

    def __init__(
        self,
        dp_client: Optional[DataProcessingClient] = None,
        ae_client: Optional[AnalyticsEngineClient] = None,
        as_client: Optional[AuditServiceClient] = None,
    ):
        self.dp_client = dp_client or DataProcessingClient()
        self.ae_client = ae_client or AnalyticsEngineClient()
        self.as_client = as_client or AuditServiceClient()

    async def run_pipeline_async(
        self,
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Executes full pipeline for an entity: Analytics -> Scoring -> Audit Manifest."""
        # 1. Fetch Entity details
        res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
        entity = res.scalar_one_or_none()
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")

        job_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)

        # 2. Trigger Analytics Engine
        analytics_result: Dict[str, Any] = {}
        try:
            analytics_result = await self.ae_client.analyze_entity(
                entity_id=entity_id,
                period_start=period_start,
                period_end=period_end,
                sector=entity.sector,
                size_tier=entity.size_tier,
                persist_to_db=True,
            )
        except Exception as exc:
            logger.warning(f"Analytics engine remote invocation failed: {exc}. Trying in-process fallback...")
            try:
                from analytics_engine.app.engines.pipeline import AnalyticsPipeline
                from analytics_engine.app.schemas.requests import AnalyzeRequest

                ae_pipeline = AnalyticsPipeline()
                ae_req = AnalyzeRequest(
                    entity_id=entity_id,
                    period_start=period_start,
                    period_end=period_end,
                    sector=entity.sector,
                    size_tier=entity.size_tier,
                    persist_to_db=True,
                )
                ae_res = await ae_pipeline.execute_async(request=ae_req, db_session=db)
                analytics_result = ae_res.model_dump(mode="json")
            except Exception as in_exc:
                logger.error(f"In-process analytics fallback also failed: {in_exc}")
                raise

        # 3. Trigger Audit Service for Merkle Manifest
        audit_result: Dict[str, Any] = {}
        try:
            audit_result = await self.as_client.generate_manifest(
                entity_id=entity_id,
                period_start=period_start,
                period_end=period_end,
                manifest_type="ANALYTICS_RUN",
            )
        except Exception as exc:
            logger.warning(f"Audit service remote invocation failed: {exc}. Trying in-process fallback...")
            try:
                from audit_service.manifest.generator import AuditManifestGenerator
                from shared.schemas.audit import AuditManifestCreate

                manifest_req = AuditManifestCreate(
                    entity_id=entity_id,
                    period_start=period_start,
                    period_end=period_end,
                    manifest_type="ANALYTICS_RUN",
                )
                doc, db_manifest = await AuditManifestGenerator.generate_manifest_async(
                    request=manifest_req,
                    db=db,
                )
                audit_result = {
                    "manifest_id": str(db_manifest.manifest_id),
                    "root_merkle_sha256": db_manifest.root_merkle_sha256,
                    "generated_at": db_manifest.generated_at.isoformat(),
                }
            except Exception as in_exc:
                logger.error(f"In-process audit fallback also failed: {in_exc}")
                raise

        completed_at = datetime.now(timezone.utc)
        duration_sec = (completed_at - started_at).total_seconds()

        return {
            "job_id": str(job_id),
            "entity_id": str(entity_id),
            "status": "COMPLETED",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": round(duration_sec, 2),
            "analytics_summary": {
                "execution_gap_count": analytics_result.get("execution_gap_count", 0),
                "negative_space_count": analytics_result.get("negative_space_count", 0),
                "correlations_count": analytics_result.get("correlations_count", 0),
                "risk_score": analytics_result.get("risk_score", {}),
            },
            "audit_manifest": audit_result,
        }
