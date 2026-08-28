"""Peer benchmark query router."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from shared.models.benchmark import PeerBenchmark
from shared.schemas.benchmark import PeerBenchmarkOut

router = APIRouter(prefix="/api/v1/analytics/benchmarks", tags=["Peer Benchmarks"])


@router.get("", response_model=List[PeerBenchmarkOut])
async def list_peer_benchmarks(
    sector: Optional[str] = Query(None),
    size_tier: Optional[str] = Query(None),
    metric_name: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves peer cohort benchmarks by sector and size tier."""
    stmt = select(PeerBenchmark)
    if sector:
        stmt = stmt.where(PeerBenchmark.sector == sector)
    if size_tier:
        stmt = stmt.where(PeerBenchmark.size_tier == size_tier)
    if metric_name:
        stmt = stmt.where(PeerBenchmark.metric_name == metric_name)

    stmt = stmt.order_by(desc(PeerBenchmark.calculated_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
