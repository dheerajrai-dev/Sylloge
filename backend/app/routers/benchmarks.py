"""Peer Benchmarking and Cohort Analysis API Router."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_supervisor
from shared.db.session import get_db
from shared.models.benchmark import PeerBenchmark
from shared.models.entity import Entity
from shared.models.risk_score import RiskScore
from shared.schemas.auth import TokenPayload
from shared.schemas.benchmark import PeerBenchmarkOut

router = APIRouter(prefix="/api/v1/benchmarks", tags=["Peer Benchmarks"])


class CohortDistributionItem(BaseModel):
    sector: str
    size_tier: str
    peer_group_size: int
    mean_risk_score: float
    p25: float
    p50: float
    p75: float
    p90: float
    is_low_confidence: bool
    entities: List[Dict[str, Any]]


class EntityZScore(BaseModel):
    entity_id: uuid.UUID
    entity_code: str
    name: str
    sector: str
    size_tier: str
    risk_score: float
    sector_mean: float
    z_score: float
    is_outlier: bool
    is_low_confidence: bool
    peer_group_size: int


@router.get("", response_model=List[PeerBenchmarkOut])
async def list_benchmarks(
    sector: Optional[str] = Query(None),
    size_tier: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Lists standard cohort benchmarks."""
    stmt = select(PeerBenchmark)
    if sector:
        stmt = stmt.where(PeerBenchmark.sector == sector)
    if size_tier:
        stmt = stmt.where(PeerBenchmark.size_tier == size_tier)
    if metric_name:
        stmt = stmt.where(PeerBenchmark.metric_name == metric_name)

    stmt = stmt.order_by(desc(PeerBenchmark.calculated_at)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/distribution", response_model=List[CohortDistributionItem])
async def get_cohort_distributions(
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Returns sector and tier risk score distributions for bell curves and histograms."""
    # Group entities by sector + tier
    ent_res = await db.execute(select(Entity).where(Entity.is_active == True))
    entities = list(ent_res.scalars().all())

    cohorts_map: Dict[str, List[Entity]] = {}
    for e in entities:
        key = f"{e.sector}|{e.size_tier}"
        cohorts_map.setdefault(key, []).append(e)

    results: List[CohortDistributionItem] = []

    for key, ent_list in cohorts_map.items():
        sector, size_tier = key.split("|")
        peer_size = len(ent_list)

        # Get latest score for each entity
        scores_list = []
        entity_points = []

        for e in ent_list:
            sc_res = await db.execute(
                select(RiskScore)
                .where(RiskScore.entity_id == e.entity_id)
                .order_by(desc(RiskScore.calculated_at))
                .limit(1)
            )
            sc = sc_res.scalar_one_or_none()
            score_val = sc.composite_risk_score if sc else 25.0
            scores_list.append(score_val)
            entity_points.append({
                "entity_id": str(e.entity_id),
                "name": e.name,
                "score": score_val,
                "tier": sc.risk_tier if sc else "LOW",
            })

        scores_list.sort()
        mean_val = round(sum(scores_list) / len(scores_list), 2) if scores_list else 0.0

        p25 = scores_list[int(len(scores_list) * 0.25)] if scores_list else 0.0
        p50 = scores_list[int(len(scores_list) * 0.50)] if scores_list else 0.0
        p75 = scores_list[int(len(scores_list) * 0.75)] if scores_list else 0.0
        p90 = scores_list[int(len(scores_list) * 0.90)] if scores_list else 0.0

        results.append(
            CohortDistributionItem(
                sector=sector,
                size_tier=size_tier,
                peer_group_size=peer_size,
                mean_risk_score=mean_val,
                p25=round(p25, 2),
                p50=round(p50, 2),
                p75=round(p75, 2),
                p90=round(p90, 2),
                is_low_confidence=peer_size < 3,
                entities=entity_points,
            )
        )

    return results


@router.get("/zscores", response_model=List[EntityZScore])
async def get_entity_zscores(
    sector: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Computes entity z-scores against sector and tier baselines with low confidence indicators."""
    ent_stmt = select(Entity).where(Entity.is_active == True)
    if sector:
        ent_stmt = ent_stmt.where(Entity.sector == sector)
    ent_res = await db.execute(ent_stmt)
    entities = list(ent_res.scalars().all())

    # Build cohort values
    cohort_scores: Dict[str, List[float]] = {}
    entity_latest: Dict[uuid.UUID, float] = {}

    for e in entities:
        key = f"{e.sector}|{e.size_tier}"
        sc_res = await db.execute(
            select(RiskScore)
            .where(RiskScore.entity_id == e.entity_id)
            .order_by(desc(RiskScore.calculated_at))
            .limit(1)
        )
        sc = sc_res.scalar_one_or_none()
        score_val = sc.composite_risk_score if sc else 20.0
        cohort_scores.setdefault(key, []).append(score_val)
        entity_latest[e.entity_id] = score_val

    zscores: List[EntityZScore] = []
    for e in entities:
        key = f"{e.sector}|{e.size_tier}"
        scores = cohort_scores.get(key, [20.0])
        peer_size = len(scores)
        mean_val = sum(scores) / len(scores)

        variance = sum((x - mean_val) ** 2 for x in scores) / max(1, len(scores))
        std_dev = variance ** 0.5

        entity_score = entity_latest[e.entity_id]
        z_val = round((entity_score - mean_val) / std_dev, 2) if std_dev > 0.01 else 0.0

        zscores.append(
            EntityZScore(
                entity_id=e.entity_id,
                entity_code=e.entity_code,
                name=e.name,
                sector=e.sector,
                size_tier=e.size_tier,
                risk_score=entity_score,
                sector_mean=round(mean_val, 2),
                z_score=z_val,
                is_outlier=abs(z_val) >= 2.0,
                is_low_confidence=peer_size < 3,
                peer_group_size=peer_size,
            )
        )

    zscores.sort(key=lambda z: z.z_score, reverse=True)
    return zscores
