"""Dashboard and Worklist API router."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_supervisor
from shared.db.session import get_db
from shared.models.entity import Entity
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.schemas.auth import TokenPayload

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard & Worklist"])


class DashboardSummary(BaseModel):
    total_entities: int
    critical_risk_entities: int
    elevated_risk_entities: int
    active_gap_findings: int
    active_silence_findings: int
    total_submissions: int
    total_quarantined_rows: int
    average_risk_score: float


class WorklistItem(BaseModel):
    entity_id: uuid.UUID
    entity_code: str
    name: str
    sector: str
    size_tier: str
    composite_risk_score: float
    execution_gap_score: float
    negative_space_score: float
    peer_deviation_score: float
    risk_tier: str
    trend_direction: str
    open_findings_count: int
    sparkline: List[float]
    last_submission_date: Optional[datetime] = None


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves executive KPI metrics for the supervisory portal."""
    # 1. Total entities
    entity_count_res = await db.execute(select(func.count(Entity.entity_id)))
    total_entities = entity_count_res.scalar() or 0

    # 2. Risk scores
    scores_res = await db.execute(
        select(RiskScore).order_by(desc(RiskScore.calculated_at))
    )
    all_scores = scores_res.scalars().all()

    # Deduplicate latest score per entity
    latest_by_entity: Dict[uuid.UUID, RiskScore] = {}
    for sc in all_scores:
        if sc.entity_id not in latest_by_entity:
            latest_by_entity[sc.entity_id] = sc

    crit_count = sum(1 for s in latest_by_entity.values() if s.risk_tier == "CRITICAL" or s.composite_risk_score >= 75.0)
    elev_count = sum(1 for s in latest_by_entity.values() if s.risk_tier in ("ELEVATED", "HIGH") or 50.0 <= s.composite_risk_score < 75.0)

    avg_score = 0.0
    if latest_by_entity:
        avg_score = round(sum(s.composite_risk_score for s in latest_by_entity.values()) / len(latest_by_entity), 2)

    # 3. Active findings count
    gap_count_res = await db.execute(
        select(func.count(ExecutionGapFinding.finding_id)).where(ExecutionGapFinding.status == "OPEN")
    )
    gap_count = gap_count_res.scalar() or 0

    neg_count_res = await db.execute(
        select(func.count(NegativeSpaceFinding.finding_id))
    )
    neg_count = neg_count_res.scalar() or 0

    # 4. Total Submissions & Quarantined
    sub_count_res = await db.execute(select(func.count(RawSubmission.submission_id)))
    total_sub = sub_count_res.scalar() or 0

    quar_sum_res = await db.execute(select(func.sum(RawSubmission.quarantined_row_count)))
    total_quar = quar_sum_res.scalar() or 0

    return DashboardSummary(
        total_entities=total_entities,
        critical_risk_entities=crit_count,
        elevated_risk_entities=elev_count,
        active_gap_findings=gap_count,
        active_silence_findings=neg_count,
        total_submissions=total_sub,
        total_quarantined_rows=int(total_quar),
        average_risk_score=avg_score,
    )


@router.get("/worklist", response_model=List[WorklistItem])
async def get_dashboard_worklist(
    sector: Optional[str] = Query(None),
    size_tier: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves ranked supervisory worklist sorted by composite risk score descending."""
    entity_stmt = select(Entity).where(Entity.is_active == True)
    if sector:
        entity_stmt = entity_stmt.where(Entity.sector == sector)
    if size_tier:
        entity_stmt = entity_stmt.where(Entity.size_tier == size_tier)

    entity_res = await db.execute(entity_stmt)
    entities = list(entity_res.scalars().all())

    worklist: List[WorklistItem] = []

    for ent in entities:
        # Fetch risk scores history for this entity
        score_stmt = (
            select(RiskScore)
            .where(RiskScore.entity_id == ent.entity_id)
            .order_by(desc(RiskScore.calculated_at))
            .limit(10)
        )
        score_res = await db.execute(score_stmt)
        scores = list(score_res.scalars().all())

        latest_score = scores[0] if scores else None
        sparkline = [s.composite_risk_score for s in reversed(scores)]

        # Fetch open findings count
        eg_cnt_res = await db.execute(
            select(func.count(ExecutionGapFinding.finding_id)).where(
                ExecutionGapFinding.entity_id == ent.entity_id,
                ExecutionGapFinding.status == "OPEN",
            )
        )
        eg_cnt = eg_cnt_res.scalar() or 0

        ns_cnt_res = await db.execute(
            select(func.count(NegativeSpaceFinding.finding_id)).where(
                NegativeSpaceFinding.entity_id == ent.entity_id
            )
        )
        ns_cnt = ns_cnt_res.scalar() or 0

        # Latest submission date
        sub_stmt = (
            select(RawSubmission.uploaded_at)
            .where(RawSubmission.entity_id == ent.entity_id)
            .order_by(desc(RawSubmission.uploaded_at))
            .limit(1)
        )
        sub_res = await db.execute(sub_stmt)
        last_sub_date = sub_res.scalar_one_or_none()

        item = WorklistItem(
            entity_id=ent.entity_id,
            entity_code=ent.entity_code,
            name=ent.name,
            sector=ent.sector,
            size_tier=ent.size_tier,
            composite_risk_score=latest_score.composite_risk_score if latest_score else 0.0,
            execution_gap_score=latest_score.execution_gap_score if latest_score else 0.0,
            negative_space_score=latest_score.negative_space_score if latest_score else 0.0,
            peer_deviation_score=latest_score.peer_deviation_score if latest_score else 0.0,
            risk_tier=latest_score.risk_tier if latest_score else "LOW",
            trend_direction=latest_score.trend_direction if latest_score else "STABLE",
            open_findings_count=eg_cnt + ns_cnt,
            sparkline=sparkline if sparkline else [0.0],
            last_submission_date=last_sub_date,
        )
        worklist.append(item)

    # Sort descending by composite_risk_score
    worklist.sort(key=lambda x: x.composite_risk_score, reverse=True)
    return worklist[:limit]
