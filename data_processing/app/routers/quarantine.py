"""Quarantine inspection API endpoints."""

import uuid
from typing import List, Optional
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from shared.models.quarantine import QuarantinedRow
from shared.schemas.quarantine import QuarantinedRowOut, QuarantineSummary

router = APIRouter(prefix="/api/v1/process/quarantine", tags=["Quarantine"])


@router.get("/{submission_id}", response_model=List[QuarantinedRowOut], status_code=status.HTTP_200_OK)
async def get_submission_quarantined_rows(
    submission_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[QuarantinedRowOut]:
    """Fetches quarantined rows for a given raw submission batch."""
    stmt = (
        select(QuarantinedRow)
        .where(QuarantinedRow.submission_id == submission_id)
        .order_by(QuarantinedRow.row_index.asc())
        .offset(offset)
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [QuarantinedRowOut.model_validate(r) for r in rows]


@router.get("/{submission_id}/summary", response_model=QuarantineSummary, status_code=status.HTTP_200_OK)
async def get_submission_quarantine_summary(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QuarantineSummary:
    """Calculates aggregate quarantine summary metrics for a submission."""
    stmt = select(QuarantinedRow).where(QuarantinedRow.submission_id == submission_id)
    res = await db.execute(stmt)
    rows = res.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quarantined rows found for submission {submission_id}",
        )

    entity_id = rows[0].entity_id
    reasons_counter = Counter(r.failure_reason for r in rows)
    fields_counter: Counter = Counter()
    for r in rows:
        if isinstance(r.failed_fields, list):
            for f in r.failed_fields:
                fields_counter[f] += 1

    return QuarantineSummary(
        submission_id=submission_id,
        entity_id=entity_id,
        total_quarantined=len(rows),
        failure_reasons_breakdown=dict(reasons_counter),
        failed_fields_breakdown=dict(fields_counter),
    )
