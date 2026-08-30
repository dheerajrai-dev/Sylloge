"""Master Analytics Pipeline orchestrating all 6 analytics and scoring engines."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.db.session import get_db
from shared.events.enums import DatasetType, FindingStatus, SeverityTier
from shared.logging import logger
from shared.models.benchmark import PeerBenchmark
from shared.models.correlation import Correlation
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.schemas.benchmark import PeerBenchmarkOut
from shared.schemas.correlation import CorrelationOut
from shared.schemas.finding import ExecutionGapFindingOut, NegativeSpaceFindingOut
from shared.schemas.risk_score import RiskScoreOut

from .correlation.engine import CorrelationEngine
from .execution_gap.engine import ExecutionGapEngine
from .explainability.engine import ExplainabilityEngine
from .negative_space.engine import NegativeSpaceEngine
from .peer_benchmark.engine import PeerBenchmarkEngine
from .risk_scoring.engine import RiskScoringEngine
from ..schemas.requests import AnalyzeRequest, AnalyzeResponse


class AnalyticsPipeline:
    """Orchestrates all six engines to produce forensic findings, benchmarks, and risk score."""

    def __init__(
        self,
        eg_engine: Optional[ExecutionGapEngine] = None,
        ns_engine: Optional[NegativeSpaceEngine] = None,
        corr_engine: Optional[CorrelationEngine] = None,
        peer_engine: Optional[PeerBenchmarkEngine] = None,
        risk_engine: Optional[RiskScoringEngine] = None,
        expl_engine: Optional[ExplainabilityEngine] = None,
    ):
        self.eg_engine = eg_engine or ExecutionGapEngine()
        self.ns_engine = ns_engine or NegativeSpaceEngine()
        self.corr_engine = corr_engine or CorrelationEngine()
        self.peer_engine = peer_engine or PeerBenchmarkEngine()
        self.risk_engine = risk_engine or RiskScoringEngine()
        self.expl_engine = expl_engine or ExplainabilityEngine()

    async def execute_async(
        self,
        request: AnalyzeRequest,
        db_session: Optional[AsyncSession] = None,
    ) -> AnalyzeResponse:
        """Runs the entire analytics pipeline asynchronously with optional DB persistence."""
        now = datetime.now(timezone.utc)
        p_start = request.period_start or now
        p_end = request.period_end or now
        entity_id = request.entity_id

        # 1. Resolve Sector and Size Tier
        sector = request.sector or "Banking"
        size_tier = request.size_tier or "Tier-1"

        if db_session and (not request.sector or not request.size_tier):
            stmt = select(Entity).where(Entity.entity_id == entity_id)
            res = await db_session.execute(stmt)
            entity_rec = res.scalars().first()
            if entity_rec:
                sector = entity_rec.sector or sector
                size_tier = entity_rec.size_tier or size_tier

        # 2. Resolve Events
        events: List[Any] = request.events or []
        if not events and db_session:
            stmt = (
                select(NormalizedEvent)
                .where(NormalizedEvent.entity_id == entity_id)
                .order_by(NormalizedEvent.event_timestamp.asc())
            )
            res = await db_session.execute(stmt)
            events = list(res.scalars().all())

        # 3. Engine 1: Execution Gap Engine
        eg_findings = self.eg_engine.run(
            events=events,
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
        )

        # 4. Engine 2: Negative Space Engine
        ns_findings = self.ns_engine.run(
            events=events,
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
        )

        # 5. Engine 3: Correlation Engine
        correlations, clusters = self.corr_engine.run(
            events=events,
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
        )

        # 6. Engine 4: Peer Benchmarking Engine
        peer_eval, benchmarks = self.peer_engine.evaluate_entity(
            target_entity_id=entity_id,
            sector=sector,
            size_tier=size_tier,
            target_events=events,
            execution_gap_findings=eg_findings,
            period_start=p_start,
            period_end=p_end,
        )

        # 7. Engine 5: Weighted Risk Scoring Engine
        alert_count = sum(
            1 for ev in events
            if str(getattr(ev, "dataset_type", "") if hasattr(ev, "dataset_type") else ev.get("dataset_type", "")) in ("alert_metadata", "ALERT")
            or str(getattr(ev, "standard_event_type", "") if hasattr(ev, "standard_event_type") else ev.get("standard_event_type", "")) == "ALERT"
        )
        risk_score_draft = self.risk_engine.calculate_score(
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
            execution_gap_findings=eg_findings,
            negative_space_findings=ns_findings,
            peer_deviation_score=peer_eval.peer_deviation_score,
            alert_count=alert_count,
            previous_score=request.previous_score,
        )

        # 8. Engine 6: Explainability Engine
        rationale_cards = self.expl_engine.generate_cards(
            entity_id=entity_id,
            execution_gap_findings=eg_findings,
            negative_space_findings=ns_findings,
            events=events,
        )

        # 9. Database Persistence
        if request.persist_to_db and db_session:
            await self._persist_async(
                db_session=db_session,
                eg_findings=eg_findings,
                ns_findings=ns_findings,
                correlations=correlations,
                benchmarks=benchmarks,
                risk_score_draft=risk_score_draft,
            )

        # 10. Format Output Response DTOs
        eg_outs = [
            ExecutionGapFindingOut(
                finding_id=f.finding_id,
                entity_id=f.entity_id,
                rule_id=f.rule_id,
                rule_name=f.rule_name,
                rule_category=f.rule_category,
                severity=f.severity,
                period_start=f.period_start,
                period_end=f.period_end,
                status="OPEN",
                description=f.description,
                rationale=f.rationale,
                evidence_record_ids=f.evidence_record_ids,
                raw_evidence_refs=f.raw_evidence_refs,
                metric_values=f.metric_values,
                created_at=now,
            )
            for f in eg_findings
        ]

        ns_outs = [
            NegativeSpaceFindingOut(
                finding_id=f.finding_id,
                entity_id=f.entity_id,
                check_id=f.check_id,
                check_name=f.check_name,
                check_category=f.check_category,
                severity=f.severity,
                period_start=f.period_start,
                period_end=f.period_end,
                expected_volume=f.expected_volume,
                observed_volume=f.observed_volume,
                drop_percentage=f.drop_percentage,
                entropy_score=f.entropy_score,
                rationale=f.rationale,
                evidence_record_ids=f.evidence_record_ids,
                created_at=now,
            )
            for f in ns_findings
        ]

        corr_outs = [
            CorrelationOut(
                correlation_id=c.correlation_id,
                entity_id=c.entity_id,
                correlation_type=c.correlation_type,
                primary_event_id=c.primary_event_id,
                correlated_event_id=c.correlated_event_id,
                asset_id=c.asset_id,
                similarity_score=c.similarity_score,
                shared_attributes=c.shared_attributes,
                rationale=c.rationale,
                created_at=c.created_at,
            )
            for c in correlations
        ]

        bench_outs = [
            PeerBenchmarkOut(
                benchmark_id=b.benchmark_id,
                sector=b.sector,
                size_tier=b.size_tier,
                metric_name=b.metric_name,
                period_start=b.period_start,
                period_end=b.period_end,
                peer_group_size=b.peer_group_size,
                mean_val=b.mean_val,
                std_dev=b.std_dev,
                p25=b.p25,
                p50=b.p50,
                p75=b.p75,
                p90=b.p90,
                is_low_confidence=b.is_low_confidence,
                calculated_at=now,
            )
            for b in benchmarks
        ]

        risk_out = RiskScoreOut(
            score_id=risk_score_draft.score_id,
            entity_id=risk_score_draft.entity_id,
            period_start=risk_score_draft.period_start,
            period_end=risk_score_draft.period_end,
            composite_risk_score=risk_score_draft.composite_risk_score,
            execution_gap_score=risk_score_draft.execution_gap_score,
            negative_space_score=risk_score_draft.negative_space_score,
            peer_deviation_score=risk_score_draft.peer_deviation_score,
            weights_applied=risk_score_draft.weights_applied,
            risk_tier=risk_score_draft.risk_tier,
            trend_direction=risk_score_draft.trend_direction,
            rationale_summary=risk_score_draft.rationale_summary,
            calculated_at=risk_score_draft.calculated_at,
        )

        return AnalyzeResponse(
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
            execution_gap_count=len(eg_findings),
            negative_space_count=len(ns_findings),
            correlations_count=len(correlations),
            burst_clusters_count=len(clusters),
            peer_group_size=peer_eval.peer_group_size,
            is_low_confidence_peer=peer_eval.is_low_confidence,
            risk_score=risk_out,
            execution_gap_findings=eg_outs,
            negative_space_findings=ns_outs,
            correlations=corr_outs,
            benchmarks=bench_outs,
            rationale_cards=rationale_cards,
        )

    def execute_sync(
        self,
        request: AnalyzeRequest,
        sync_session: Optional[Session] = None,
    ) -> AnalyzeResponse:
        """Synchronous pipeline execution for tests and batch workflows."""
        now = datetime.now(timezone.utc)
        p_start = request.period_start or now
        p_end = request.period_end or now
        entity_id = request.entity_id

        sector = request.sector or "Banking"
        size_tier = request.size_tier or "Tier-1"

        if sync_session and (not request.sector or not request.size_tier):
            entity_rec = sync_session.query(Entity).filter(Entity.entity_id == entity_id).first()
            if entity_rec:
                sector = entity_rec.sector or sector
                size_tier = entity_rec.size_tier or size_tier

        events = request.events or []
        if not events and sync_session:
            events = sync_session.query(NormalizedEvent).filter(NormalizedEvent.entity_id == entity_id).all()

        eg_findings = self.eg_engine.run(events, entity_id, p_start, p_end)
        ns_findings = self.ns_engine.run(events, entity_id, p_start, p_end)
        correlations, clusters = self.corr_engine.run(events, entity_id, p_start, p_end)
        peer_eval, benchmarks = self.peer_engine.evaluate_entity(
            target_entity_id=entity_id,
            sector=sector,
            size_tier=size_tier,
            target_events=events,
            execution_gap_findings=eg_findings,
            period_start=p_start,
            period_end=p_end,
        )

        alert_count = sum(
            1 for ev in events
            if str(getattr(ev, "dataset_type", "") if hasattr(ev, "dataset_type") else ev.get("dataset_type", "")) in ("alert_metadata", "ALERT")
            or str(getattr(ev, "standard_event_type", "") if hasattr(ev, "standard_event_type") else ev.get("standard_event_type", "")) == "ALERT"
        )
        risk_score_draft = self.risk_engine.calculate_score(
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
            execution_gap_findings=eg_findings,
            negative_space_findings=ns_findings,
            peer_deviation_score=peer_eval.peer_deviation_score,
            alert_count=alert_count,
            previous_score=request.previous_score,
        )

        rationale_cards = self.expl_engine.generate_cards(
            entity_id=entity_id,
            execution_gap_findings=eg_findings,
            negative_space_findings=ns_findings,
            events=events,
        )

        if request.persist_to_db and sync_session:
            self._persist_sync(
                sync_session=sync_session,
                eg_findings=eg_findings,
                ns_findings=ns_findings,
                correlations=correlations,
                benchmarks=benchmarks,
                risk_score_draft=risk_score_draft,
            )

        eg_outs = [
            ExecutionGapFindingOut(
                finding_id=f.finding_id,
                entity_id=f.entity_id,
                rule_id=f.rule_id,
                rule_name=f.rule_name,
                rule_category=f.rule_category,
                severity=f.severity,
                period_start=f.period_start,
                period_end=f.period_end,
                status="OPEN",
                description=f.description,
                rationale=f.rationale,
                evidence_record_ids=f.evidence_record_ids,
                raw_evidence_refs=f.raw_evidence_refs,
                metric_values=f.metric_values,
                created_at=now,
            )
            for f in eg_findings
        ]

        ns_outs = [
            NegativeSpaceFindingOut(
                finding_id=f.finding_id,
                entity_id=f.entity_id,
                check_id=f.check_id,
                check_name=f.check_name,
                check_category=f.check_category,
                severity=f.severity,
                period_start=f.period_start,
                period_end=f.period_end,
                expected_volume=f.expected_volume,
                observed_volume=f.observed_volume,
                drop_percentage=f.drop_percentage,
                entropy_score=f.entropy_score,
                rationale=f.rationale,
                evidence_record_ids=f.evidence_record_ids,
                created_at=now,
            )
            for f in ns_findings
        ]

        corr_outs = [
            CorrelationOut(
                correlation_id=c.correlation_id,
                entity_id=c.entity_id,
                correlation_type=c.correlation_type,
                primary_event_id=c.primary_event_id,
                correlated_event_id=c.correlated_event_id,
                asset_id=c.asset_id,
                similarity_score=c.similarity_score,
                shared_attributes=c.shared_attributes,
                rationale=c.rationale,
                created_at=c.created_at,
            )
            for c in correlations
        ]

        bench_outs = [
            PeerBenchmarkOut(
                benchmark_id=b.benchmark_id,
                sector=b.sector,
                size_tier=b.size_tier,
                metric_name=b.metric_name,
                period_start=b.period_start,
                period_end=b.period_end,
                peer_group_size=b.peer_group_size,
                mean_val=b.mean_val,
                std_dev=b.std_dev,
                p25=b.p25,
                p50=b.p50,
                p75=b.p75,
                p90=b.p90,
                is_low_confidence=b.is_low_confidence,
                calculated_at=now,
            )
            for b in benchmarks
        ]

        risk_out = RiskScoreOut(
            score_id=risk_score_draft.score_id,
            entity_id=risk_score_draft.entity_id,
            period_start=risk_score_draft.period_start,
            period_end=risk_score_draft.period_end,
            composite_risk_score=risk_score_draft.composite_risk_score,
            execution_gap_score=risk_score_draft.execution_gap_score,
            negative_space_score=risk_score_draft.negative_space_score,
            peer_deviation_score=risk_score_draft.peer_deviation_score,
            weights_applied=risk_score_draft.weights_applied,
            risk_tier=risk_score_draft.risk_tier,
            trend_direction=risk_score_draft.trend_direction,
            rationale_summary=risk_score_draft.rationale_summary,
            calculated_at=risk_score_draft.calculated_at,
        )

        return AnalyzeResponse(
            entity_id=entity_id,
            period_start=p_start,
            period_end=p_end,
            execution_gap_count=len(eg_findings),
            negative_space_count=len(ns_findings),
            correlations_count=len(correlations),
            burst_clusters_count=len(clusters),
            peer_group_size=peer_eval.peer_group_size,
            is_low_confidence_peer=peer_eval.is_low_confidence,
            risk_score=risk_out,
            execution_gap_findings=eg_outs,
            negative_space_findings=ns_outs,
            correlations=corr_outs,
            benchmarks=bench_outs,
            rationale_cards=rationale_cards,
        )

    async def _persist_async(
        self,
        db_session: AsyncSession,
        eg_findings: List[Any],
        ns_findings: List[Any],
        correlations: List[Any],
        benchmarks: List[Any],
        risk_score_draft: Any,
    ) -> None:
        """Asynchronously writes findings, correlations, and risk scores to PostgreSQL."""
        try:
            target_eid = uuid.UUID(str(risk_score_draft.entity_id))
            # Clear previous findings & correlations for this entity before inserting new evaluation
            await db_session.execute(delete(ExecutionGapFinding).where(ExecutionGapFinding.entity_id == target_eid))
            await db_session.execute(delete(NegativeSpaceFinding).where(NegativeSpaceFinding.entity_id == target_eid))
            await db_session.execute(delete(Correlation).where(Correlation.entity_id == target_eid))
            await db_session.flush()

            # 1. Execution Gap Findings
            for f in eg_findings:
                finding_model = ExecutionGapFinding(
                    finding_id=f.finding_id,
                    entity_id=f.entity_id,
                    rule_id=f.rule_id,
                    rule_name=f.rule_name,
                    rule_category=f.rule_category,
                    severity=f.severity,
                    period_start=f.period_start,
                    period_end=f.period_end,
                    status="OPEN",
                    description=f.description,
                    rationale=f.rationale,
                    evidence_record_ids=f.evidence_record_ids,
                    raw_evidence_refs=f.raw_evidence_refs,
                    metric_values=f.metric_values,
                )
                db_session.add(finding_model)

            # 2. Negative Space Findings
            for f in ns_findings:
                finding_model = NegativeSpaceFinding(
                    finding_id=f.finding_id,
                    entity_id=f.entity_id,
                    check_id=f.check_id,
                    check_name=f.check_name,
                    check_category=f.check_category,
                    severity=f.severity,
                    period_start=f.period_start,
                    period_end=f.period_end,
                    expected_volume=f.expected_volume,
                    observed_volume=f.observed_volume,
                    drop_percentage=f.drop_percentage,
                    entropy_score=f.entropy_score,
                    rationale=f.rationale,
                    evidence_record_ids=f.evidence_record_ids,
                    raw_evidence_refs=getattr(f, "raw_evidence_refs", []),
                    metric_values=getattr(f, "metric_values", {}),
                )
                db_session.add(finding_model)

            # 3. Correlations
            for c in correlations:
                corr_model = Correlation(
                    correlation_id=c.correlation_id,
                    entity_id=c.entity_id,
                    correlation_type=c.correlation_type,
                    primary_event_id=c.primary_event_id,
                    correlated_event_id=c.correlated_event_id,
                    asset_id=c.asset_id,
                    similarity_score=c.similarity_score,
                    shared_attributes=c.shared_attributes,
                    rationale=c.rationale,
                )
                db_session.add(corr_model)

            # 4. Peer Benchmarks
            for b in benchmarks:
                bench_model = PeerBenchmark(
                    benchmark_id=b.benchmark_id,
                    sector=b.sector,
                    size_tier=b.size_tier,
                    metric_name=b.metric_name,
                    period_start=b.period_start,
                    period_end=b.period_end,
                    peer_group_size=b.peer_group_size,
                    mean_val=b.mean_val,
                    std_dev=b.std_dev,
                    p25=b.p25,
                    p50=b.p50,
                    p75=b.p75,
                    p90=b.p90,
                    is_low_confidence=b.is_low_confidence,
                )
                db_session.add(bench_model)

            # 5. Risk Score
            score_model = RiskScore(
                score_id=risk_score_draft.score_id,
                entity_id=risk_score_draft.entity_id,
                period_start=risk_score_draft.period_start,
                period_end=risk_score_draft.period_end,
                composite_risk_score=risk_score_draft.composite_risk_score,
                execution_gap_score=risk_score_draft.execution_gap_score,
                negative_space_score=risk_score_draft.negative_space_score,
                peer_deviation_score=risk_score_draft.peer_deviation_score,
                weights_applied=risk_score_draft.weights_applied,
                risk_tier=risk_score_draft.risk_tier,
                trend_direction=risk_score_draft.trend_direction,
                rationale_summary=risk_score_draft.rationale_summary,
            )
            db_session.add(score_model)

            await db_session.commit()
            logger.info("Successfully persisted analytics findings and scores to database.")
        except Exception as exc:
            await db_session.rollback()
            logger.error(f"Failed to persist analytics results: {exc}", exc_info=True)

    def _persist_sync(
        self,
        sync_session: Session,
        eg_findings: List[Any],
        ns_findings: List[Any],
        correlations: List[Any],
        benchmarks: List[Any],
        risk_score_draft: Any,
    ) -> None:
        """Synchronously writes findings, correlations, and risk scores to PostgreSQL."""
        try:
            target_eid = uuid.UUID(str(risk_score_draft.entity_id))
            # Clear previous findings & correlations for this entity before inserting new evaluation
            sync_session.query(ExecutionGapFinding).filter(ExecutionGapFinding.entity_id == target_eid).delete()
            sync_session.query(NegativeSpaceFinding).filter(NegativeSpaceFinding.entity_id == target_eid).delete()
            sync_session.query(Correlation).filter(Correlation.entity_id == target_eid).delete()
            sync_session.flush()
            for f in eg_findings:
                finding_model = ExecutionGapFinding(
                    finding_id=f.finding_id,
                    entity_id=f.entity_id,
                    rule_id=f.rule_id,
                    rule_name=f.rule_name,
                    rule_category=f.rule_category,
                    severity=f.severity,
                    period_start=f.period_start,
                    period_end=f.period_end,
                    status="OPEN",
                    description=f.description,
                    rationale=f.rationale,
                    evidence_record_ids=f.evidence_record_ids,
                    raw_evidence_refs=f.raw_evidence_refs,
                    metric_values=f.metric_values,
                )
                sync_session.add(finding_model)

            for f in ns_findings:
                finding_model = NegativeSpaceFinding(
                    finding_id=f.finding_id,
                    entity_id=f.entity_id,
                    check_id=f.check_id,
                    check_name=f.check_name,
                    check_category=f.check_category,
                    severity=f.severity,
                    period_start=f.period_start,
                    period_end=f.period_end,
                    expected_volume=f.expected_volume,
                    observed_volume=f.observed_volume,
                    drop_percentage=f.drop_percentage,
                    entropy_score=f.entropy_score,
                    rationale=f.rationale,
                    evidence_record_ids=f.evidence_record_ids,
                    raw_evidence_refs=getattr(f, "raw_evidence_refs", []),
                    metric_values=getattr(f, "metric_values", {}),
                )
                sync_session.add(finding_model)

            for c in correlations:
                corr_model = Correlation(
                    correlation_id=c.correlation_id,
                    entity_id=c.entity_id,
                    correlation_type=c.correlation_type,
                    primary_event_id=c.primary_event_id,
                    correlated_event_id=c.correlated_event_id,
                    asset_id=c.asset_id,
                    similarity_score=c.similarity_score,
                    shared_attributes=c.shared_attributes,
                    rationale=c.rationale,
                )
                sync_session.add(corr_model)

            for b in benchmarks:
                bench_model = PeerBenchmark(
                    benchmark_id=b.benchmark_id,
                    sector=b.sector,
                    size_tier=b.size_tier,
                    metric_name=b.metric_name,
                    period_start=b.period_start,
                    period_end=b.period_end,
                    peer_group_size=b.peer_group_size,
                    mean_val=b.mean_val,
                    std_dev=b.std_dev,
                    p25=b.p25,
                    p50=b.p50,
                    p75=b.p75,
                    p90=b.p90,
                    is_low_confidence=b.is_low_confidence,
                )
                sync_session.add(bench_model)

            score_model = RiskScore(
                score_id=risk_score_draft.score_id,
                entity_id=risk_score_draft.entity_id,
                period_start=risk_score_draft.period_start,
                period_end=risk_score_draft.period_end,
                composite_risk_score=risk_score_draft.composite_risk_score,
                execution_gap_score=risk_score_draft.execution_gap_score,
                negative_space_score=risk_score_draft.negative_space_score,
                peer_deviation_score=risk_score_draft.peer_deviation_score,
                weights_applied=risk_score_draft.weights_applied,
                risk_tier=risk_score_draft.risk_tier,
                trend_direction=risk_score_draft.trend_direction,
                rationale_summary=risk_score_draft.rationale_summary,
            )
            sync_session.add(score_model)

            sync_session.commit()
            logger.info("Successfully persisted analytics findings and scores to sync database.")
        except Exception as exc:
            sync_session.rollback()
            logger.error(f"Failed to sync-persist analytics results: {exc}", exc_info=True)
