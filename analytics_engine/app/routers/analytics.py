"""Analytics analysis and findings query router."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.service_auth import verify_internal_service_key
from shared.db.session import get_db
from shared.models.correlation import Correlation
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.risk_score import RiskScore
from shared.schemas.correlation import CorrelationOut
from shared.schemas.finding import ExecutionGapFindingOut, NegativeSpaceFindingOut
from shared.schemas.risk_score import RiskScoreOut
from ..engines.execution_gap.engine import ExecutionGapEngine
from ..engines.negative_space.engine import NegativeSpaceEngine
from ..engines.pipeline import AnalyticsPipeline
from ..schemas.requests import AnalyzeRequest, AnalyzeResponse
from .rules import eg_registry, ns_registry

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Scoring"])

# Initialize pipeline with shared registries
pipeline = AnalyticsPipeline(
    eg_engine=ExecutionGapEngine(registry=eg_registry),
    ns_engine=NegativeSpaceEngine(registry=ns_registry),
)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_entity(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_internal_service_key),
):
    """Executes the full 6-engine analytics and scoring pipeline for an entity."""
    try:
        response = await pipeline.execute_async(request=request, db_session=db)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analytics execution failed: {str(exc)}",
        ) from exc


@router.get("/findings/execution-gap", response_model=List[ExecutionGapFindingOut])
async def list_execution_gap_findings(
    entity_id: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None),
    rule_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Queries Execution Gap findings with optional filtering."""
    stmt = select(ExecutionGapFinding)
    if entity_id:
        stmt = stmt.where(ExecutionGapFinding.entity_id == entity_id)
    if severity:
        stmt = stmt.where(ExecutionGapFinding.severity == severity.upper())
    if rule_id:
        stmt = stmt.where(ExecutionGapFinding.rule_id == rule_id)

    stmt = stmt.order_by(desc(ExecutionGapFinding.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/findings/negative-space", response_model=List[NegativeSpaceFindingOut])
async def list_negative_space_findings(
    entity_id: Optional[uuid.UUID] = Query(None),
    severity: Optional[str] = Query(None),
    check_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Queries Negative Space absence findings with optional filtering."""
    stmt = select(NegativeSpaceFinding)
    if entity_id:
        stmt = stmt.where(NegativeSpaceFinding.entity_id == entity_id)
    if severity:
        stmt = stmt.where(NegativeSpaceFinding.severity == severity.upper())
    if check_id:
        stmt = stmt.where(NegativeSpaceFinding.check_id == check_id)

    stmt = stmt.order_by(desc(NegativeSpaceFinding.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/scores/{entity_id}", response_model=List[RiskScoreOut])
async def get_entity_risk_scores(
    entity_id: uuid.UUID,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves historical composite risk scores for a given entity."""
    stmt = (
        select(RiskScore)
        .where(RiskScore.entity_id == entity_id)
        .order_by(desc(RiskScore.calculated_at))
        .limit(limit)
    )
    res = await db.execute(stmt)
    scores = list(res.scalars().all())
    return scores


@router.get("/correlations", response_model=List[CorrelationOut])
async def list_correlations(
    entity_id: Optional[uuid.UUID] = Query(None),
    correlation_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Queries correlation links (repeat-asset alerts, note clones)."""
    stmt = select(Correlation)
    if entity_id:
        stmt = stmt.where(Correlation.entity_id == entity_id)
    if correlation_type:
        stmt = stmt.where(Correlation.correlation_type == correlation_type)

    stmt = stmt.order_by(desc(Correlation.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
