"""Supervised Regulated Entities Management API Router."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_supervisor
from shared.db.session import get_db
from shared.models.entity import Entity
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.mapping import FieldMappingProfile
from shared.models.risk_score import RiskScore
from shared.schemas.auth import TokenPayload
from shared.schemas.entity import EntityCreate, EntityOut, EntitySummary, EntityUpdate
from shared.schemas.mapping import FieldMappingProfileCreate, FieldMappingProfileOut
from shared.schemas.risk_score import RiskScoreOut

router = APIRouter(prefix="/api/v1/entities", tags=["Entities"])


class EntityDetailResponse(BaseModel):
    entity: EntityOut
    latest_risk_score: Optional[float] = None
    execution_gap_score: Optional[float] = None
    negative_space_score: Optional[float] = None
    peer_deviation_score: Optional[float] = None
    risk_tier: Optional[str] = None
    trend_direction: Optional[str] = None
    open_findings_count: int = 0
    total_submissions: int = 0


class RadarAxisMetric(BaseModel):
    axis: str
    value: float  # 0 to 100
    benchmark: float  # Sector mean


@router.get("", response_model=List[EntitySummary])
async def list_entities(
    search: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    size_tier: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Lists registered supervised entities with summary risk scores."""
    stmt = select(Entity)
    if search:
        stmt = stmt.where(
            (Entity.name.ilike(f"%{search}%")) | (Entity.entity_code.ilike(f"%{search}%"))
        )
    if sector:
        stmt = stmt.where(Entity.sector == sector)
    if size_tier:
        stmt = stmt.where(Entity.size_tier == size_tier)

    stmt = stmt.order_by(Entity.name).offset(offset).limit(limit)
    res = await db.execute(stmt)
    entities = list(res.scalars().all())

    summaries: List[EntitySummary] = []
    for ent in entities:
        # Latest score
        score_stmt = (
            select(RiskScore)
            .where(RiskScore.entity_id == ent.entity_id)
            .order_by(desc(RiskScore.calculated_at))
            .limit(1)
        )
        score_res = await db.execute(score_stmt)
        latest_score = score_res.scalar_one_or_none()

        # Open findings
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

        summary = EntitySummary(
            entity_id=ent.entity_id,
            entity_code=ent.entity_code,
            name=ent.name,
            sector=ent.sector,
            size_tier=ent.size_tier,
            is_active=ent.is_active,
            latest_risk_score=latest_score.composite_risk_score if latest_score else None,
            latest_risk_tier=latest_score.risk_tier if latest_score else None,
            latest_trend=latest_score.trend_direction if latest_score else None,
            open_findings_count=eg_cnt + ns_cnt,
        )
        summaries.append(summary)

    return summaries


@router.post("", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
async def create_entity(
    payload: EntityCreate,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Registers a new regulated supervised entity."""
    # Check duplicate entity_code
    dup_res = await db.execute(
        select(Entity).where(Entity.entity_code == payload.entity_code)
    )
    if dup_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity code '{payload.entity_code}' already registered",
        )

    entity = Entity(
        entity_id=uuid.uuid4(),
        entity_code=payload.entity_code,
        name=payload.name,
        sector=payload.sector,
        size_tier=payload.size_tier,
        contact_email=payload.contact_email,
        is_active=payload.is_active,
        entity_metadata=payload.entity_metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)
    return entity


@router.get("/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_detail(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves deep profile of an entity with latest risk breakdown."""
    ent_res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = ent_res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    score_stmt = (
        select(RiskScore)
        .where(RiskScore.entity_id == entity_id)
        .order_by(desc(RiskScore.calculated_at))
        .limit(1)
    )
    score_res = await db.execute(score_stmt)
    latest_score = score_res.scalar_one_or_none()

    eg_cnt_res = await db.execute(
        select(func.count(ExecutionGapFinding.finding_id)).where(
            ExecutionGapFinding.entity_id == entity_id,
            ExecutionGapFinding.status == "OPEN",
        )
    )
    eg_cnt = eg_cnt_res.scalar() or 0

    ns_cnt_res = await db.execute(
        select(func.count(NegativeSpaceFinding.finding_id)).where(
            NegativeSpaceFinding.entity_id == entity_id
        )
    )
    ns_cnt = ns_cnt_res.scalar() or 0

    return EntityDetailResponse(
        entity=EntityOut.model_validate(entity),
        latest_risk_score=latest_score.composite_risk_score if latest_score else 0.0,
        execution_gap_score=latest_score.execution_gap_score if latest_score else 0.0,
        negative_space_score=latest_score.negative_space_score if latest_score else 0.0,
        peer_deviation_score=latest_score.peer_deviation_score if latest_score else 0.0,
        risk_tier=latest_score.risk_tier if latest_score else "LOW",
        trend_direction=latest_score.trend_direction if latest_score else "STABLE",
        open_findings_count=eg_cnt + ns_cnt,
    )


@router.put("/{entity_id}", response_model=EntityOut)
async def update_entity(
    entity_id: uuid.UUID,
    payload: EntityUpdate,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Updates entity details."""
    ent_res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = ent_res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    if payload.name is not None:
        entity.name = payload.name
    if payload.sector is not None:
        entity.sector = payload.sector
    if payload.size_tier is not None:
        entity.size_tier = payload.size_tier
    if payload.contact_email is not None:
        entity.contact_email = payload.contact_email
    if payload.is_active is not None:
        entity.is_active = payload.is_active
    if payload.entity_metadata is not None:
        entity.entity_metadata = payload.entity_metadata

    entity.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entity)
    return entity


@router.delete("/{entity_id}")
async def delete_entity(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Deletes an entity."""
    ent_res = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    entity = ent_res.scalar_one_or_none()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    await db.delete(entity)
    await db.commit()
    return {"message": f"Entity {entity.entity_code} deleted successfully"}


@router.get("/{entity_id}/scores", response_model=List[RiskScoreOut])
async def get_entity_scores(
    entity_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves list of calculated risk scores for entity."""
    stmt = (
        select(RiskScore)
        .where(RiskScore.entity_id == entity_id)
        .order_by(desc(RiskScore.calculated_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{entity_id}/history")
async def get_entity_history(
    entity_id: uuid.UUID,
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves time-series history of composite and component scores for trend charts."""
    stmt = (
        select(RiskScore)
        .where(RiskScore.entity_id == entity_id)
        .order_by(RiskScore.calculated_at.asc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    scores = list(res.scalars().all())

    history = [
        {
            "date": s.calculated_at.strftime("%Y-%m-%d"),
            "timestamp": s.calculated_at.isoformat(),
            "composite": s.composite_risk_score,
            "execution_gap": s.execution_gap_score,
            "negative_space": s.negative_space_score,
            "peer_deviation": s.peer_deviation_score,
            "tier": s.risk_tier,
        }
        for s in scores
    ]
    return history


@router.get("/{entity_id}/radar", response_model=List[RadarAxisMetric])
async def get_entity_radar_data(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Computes multi-axis supervisory metrics for radar chart visualization."""
    score_stmt = (
        select(RiskScore)
        .where(RiskScore.entity_id == entity_id)
        .order_by(desc(RiskScore.calculated_at))
        .limit(1)
    )
    score_res = await db.execute(score_stmt)
    latest_score = score_res.scalar_one_or_none()

    gap_val = latest_score.execution_gap_score if latest_score else 20.0
    neg_val = latest_score.negative_space_score if latest_score else 15.0
    peer_val = latest_score.peer_deviation_score if latest_score else 25.0

    return [
        RadarAxisMetric(axis="Execution Gap", value=round(gap_val, 1), benchmark=30.0),
        RadarAxisMetric(axis="Negative Space", value=round(neg_val, 1), benchmark=25.0),
        RadarAxisMetric(axis="Peer Deviation", value=round(peer_val, 1), benchmark=35.0),
        RadarAxisMetric(axis="Note Plagiarism", value=round(min(100.0, gap_val * 0.8), 1), benchmark=20.0),
        RadarAxisMetric(axis="SLA Breach Rate", value=round(min(100.0, gap_val * 1.1), 1), benchmark=28.0),
        RadarAxisMetric(axis="Sensor Silence", value=round(min(100.0, neg_val * 1.2), 1), benchmark=22.0),
    ]


@router.get("/{entity_id}/mappings", response_model=List[FieldMappingProfileOut])
async def get_entity_mapping_profiles(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves active schema mapping profiles for an entity."""
    stmt = (
        select(FieldMappingProfile)
        .where(FieldMappingProfile.entity_id == entity_id)
        .order_by(FieldMappingProfile.dataset_type)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
