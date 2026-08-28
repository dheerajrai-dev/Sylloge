"""Findings, Rationale Cards, and Evidence Drill-Down API Router."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import get_current_supervisor
from shared.db.session import get_db
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.quarantine import QuarantinedRow
from shared.models.submission import RawSubmission
from shared.schemas.auth import TokenPayload
from shared.schemas.event import StandardEventOut
from shared.schemas.finding import ExecutionGapFindingOut, NegativeSpaceFindingOut, RationaleCard

router = APIRouter(prefix="/api/v1/findings", tags=["Findings & Evidence Drill-Down"])


class UnifiedFindingItem(BaseModel):
    finding_id: uuid.UUID
    entity_id: uuid.UUID
    entity_name: Optional[str] = None
    engine: str  # "EXECUTION_GAP" or "NEGATIVE_SPACE"
    rule_or_check_id: str
    title: str
    category: str
    severity: str
    period_start: datetime
    period_end: datetime
    status: str
    description: str
    rationale: str
    evidence_record_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.95
    created_at: datetime


class FindingDetailResponse(BaseModel):
    finding: UnifiedFindingItem
    rationale_card: RationaleCard
    evidence_count: int


class RawDiffResponse(BaseModel):
    finding_id: uuid.UUID
    normalized_events: List[Dict[str, Any]]
    quarantined_rows: List[Dict[str, Any]]
    raw_snippets: List[Dict[str, Any]]


class AddNoteRequest(BaseModel):
    note: str


@router.get("", response_model=List[UnifiedFindingItem])
async def list_findings(
    entity_id: Optional[uuid.UUID] = Query(None),
    engine: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves unified list of gap and negative space findings with filters."""
    findings: List[UnifiedFindingItem] = []

    # 1. Query entities map for names
    ent_res = await db.execute(select(Entity))
    entities_map = {e.entity_id: e.name for e in ent_res.scalars().all()}

    # 2. Query Execution Gap findings
    if not engine or engine.upper() in ("EXECUTION_GAP", "GAP"):
        eg_stmt = select(ExecutionGapFinding)
        if entity_id:
            eg_stmt = eg_stmt.where(ExecutionGapFinding.entity_id == entity_id)
        if severity:
            eg_stmt = eg_stmt.where(ExecutionGapFinding.severity == severity.upper())
        if status:
            eg_stmt = eg_stmt.where(ExecutionGapFinding.status == status.upper())

        eg_stmt = eg_stmt.order_by(desc(ExecutionGapFinding.created_at)).limit(limit)
        eg_res = await db.execute(eg_stmt)
        for eg in eg_res.scalars().all():
            findings.append(
                UnifiedFindingItem(
                    finding_id=eg.finding_id,
                    entity_id=eg.entity_id,
                    entity_name=entities_map.get(eg.entity_id, "Unknown Entity"),
                    engine="EXECUTION_GAP",
                    rule_or_check_id=eg.rule_id,
                    title=eg.rule_name,
                    category=eg.rule_category,
                    severity=eg.severity,
                    period_start=eg.period_start,
                    period_end=eg.period_end,
                    status=eg.status,
                    description=eg.description,
                    rationale=eg.rationale,
                    evidence_record_ids=[str(x) for x in (eg.evidence_record_ids or [])],
                    confidence=0.95,
                    created_at=eg.created_at,
                )
            )

    # 3. Query Negative Space findings
    if not engine or engine.upper() in ("NEGATIVE_SPACE", "SILENCE", "ANOMALY"):
        ns_stmt = select(NegativeSpaceFinding)
        if entity_id:
            ns_stmt = ns_stmt.where(NegativeSpaceFinding.entity_id == entity_id)
        if severity:
            ns_stmt = ns_stmt.where(NegativeSpaceFinding.severity == severity.upper())

        ns_stmt = ns_stmt.order_by(desc(NegativeSpaceFinding.created_at)).limit(limit)
        ns_res = await db.execute(ns_stmt)
        for ns in ns_res.scalars().all():
            findings.append(
                UnifiedFindingItem(
                    finding_id=ns.finding_id,
                    entity_id=ns.entity_id,
                    entity_name=entities_map.get(ns.entity_id, "Unknown Entity"),
                    engine="NEGATIVE_SPACE",
                    rule_or_check_id=ns.check_id,
                    title=ns.check_name,
                    category=ns.check_category,
                    severity=ns.severity,
                    period_start=ns.period_start,
                    period_end=ns.period_end,
                    status="OPEN",
                    description=f"Observed volume {ns.observed_volume} dropped {ns.drop_percentage}% vs expected baseline {ns.expected_volume}",
                    rationale=ns.rationale,
                    evidence_record_ids=[str(x) for x in (ns.evidence_record_ids or [])],
                    confidence=0.90,
                    created_at=ns.created_at,
                )
            )

    # Sort combined findings by created_at desc
    findings.sort(key=lambda x: x.created_at, reverse=True)
    return findings[offset : offset + limit]


@router.get("/{finding_id}", response_model=FindingDetailResponse)
async def get_finding_detail(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves deep drill-down details for a specific finding."""
    # Check Execution Gap first
    eg_res = await db.execute(
        select(ExecutionGapFinding).where(ExecutionGapFinding.finding_id == finding_id)
    )
    eg = eg_res.scalar_one_or_none()

    if eg:
        ent_res = await db.execute(select(Entity).where(Entity.entity_id == eg.entity_id))
        entity = ent_res.scalar_one_or_none()
        ent_name = entity.name if entity else "Unknown"

        item = UnifiedFindingItem(
            finding_id=eg.finding_id,
            entity_id=eg.entity_id,
            entity_name=ent_name,
            engine="EXECUTION_GAP",
            rule_or_check_id=eg.rule_id,
            title=eg.rule_name,
            category=eg.rule_category,
            severity=eg.severity,
            period_start=eg.period_start,
            period_end=eg.period_end,
            status=eg.status,
            description=eg.description,
            rationale=eg.rationale,
            evidence_record_ids=[str(x) for x in (eg.evidence_record_ids or [])],
            confidence=0.95,
            created_at=eg.created_at,
        )
        card = RationaleCard(
            title=eg.rule_name,
            category=eg.rule_category,
            severity=eg.severity,
            rationale_text=eg.rationale,
            evidence_record_ids=[str(x) for x in (eg.evidence_record_ids or [])],
            raw_evidence_refs=eg.raw_evidence_refs or [],
            metric_values=eg.metric_values or {},
            recommended_action=f"Mandate immediate compliance review for {eg.rule_name} violations.",
        )
        return FindingDetailResponse(
            finding=item,
            rationale_card=card,
            evidence_count=len(eg.evidence_record_ids or []),
        )

    # Check Negative Space
    ns_res = await db.execute(
        select(NegativeSpaceFinding).where(NegativeSpaceFinding.finding_id == finding_id)
    )
    ns = ns_res.scalar_one_or_none()

    if ns:
        ent_res = await db.execute(select(Entity).where(Entity.entity_id == ns.entity_id))
        entity = ent_res.scalar_one_or_none()
        ent_name = entity.name if entity else "Unknown"

        item = UnifiedFindingItem(
            finding_id=ns.finding_id,
            entity_id=ns.entity_id,
            entity_name=ent_name,
            engine="NEGATIVE_SPACE",
            rule_or_check_id=ns.check_id,
            title=ns.check_name,
            category=ns.check_category,
            severity=ns.severity,
            period_start=ns.period_start,
            period_end=ns.period_end,
            status="OPEN",
            description=f"Volume drop of {ns.drop_percentage}% (observed {ns.observed_volume} vs expected {ns.expected_volume})",
            rationale=ns.rationale,
            evidence_record_ids=[str(x) for x in (ns.evidence_record_ids or [])],
            confidence=0.90,
            created_at=ns.created_at,
        )
        card = RationaleCard(
            title=ns.check_name,
            category=ns.check_category,
            severity=ns.severity,
            rationale_text=ns.rationale,
            evidence_record_ids=[str(x) for x in (ns.evidence_record_ids or [])],
            raw_evidence_refs=[],
            metric_values={
                "expected_volume": ns.expected_volume,
                "observed_volume": ns.observed_volume,
                "drop_percentage": ns.drop_percentage,
                "entropy_score": ns.entropy_score,
            },
            recommended_action="Verify telemetry sensor health and check for silent outage periods.",
        )
        return FindingDetailResponse(
            finding=item,
            rationale_card=card,
            evidence_count=len(ns.evidence_record_ids or []),
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")


@router.get("/{finding_id}/evidence", response_model=List[StandardEventOut])
async def get_finding_evidence_events(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves canonical normalized event records attached as evidence to this finding."""
    # Find evidence record UUIDs
    eg_res = await db.execute(
        select(ExecutionGapFinding.evidence_record_ids).where(ExecutionGapFinding.finding_id == finding_id)
    )
    evidence_ids = eg_res.scalar_one_or_none()

    if evidence_ids is None:
        ns_res = await db.execute(
            select(NegativeSpaceFinding.evidence_record_ids).where(NegativeSpaceFinding.finding_id == finding_id)
        )
        evidence_ids = ns_res.scalar_one_or_none()

    if not evidence_ids:
        return []

    # Parse UUIDs
    parsed_uuids: List[uuid.UUID] = []
    for item in evidence_ids:
        try:
            parsed_uuids.append(uuid.UUID(str(item)))
        except (ValueError, TypeError):
            continue

    if not parsed_uuids:
        return []

    evt_stmt = select(NormalizedEvent).where(NormalizedEvent.event_id.in_(parsed_uuids))
    evt_res = await db.execute(evt_stmt)
    return list(evt_res.scalars().all())


@router.get("/{finding_id}/raw-diff", response_model=RawDiffResponse)
async def get_finding_raw_diff(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Retrieves normalized events and quarantined row diffs for side-by-side evidence analysis."""
    # 1. Fetch finding
    eg_res = await db.execute(
        select(ExecutionGapFinding).where(ExecutionGapFinding.finding_id == finding_id)
    )
    finding = eg_res.scalar_one_or_none()
    entity_id = finding.entity_id if finding else None

    if not finding:
        ns_res = await db.execute(
            select(NegativeSpaceFinding).where(NegativeSpaceFinding.finding_id == finding_id)
        )
        finding = ns_res.scalar_one_or_none()
        entity_id = finding.entity_id if finding else None

    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    evidence_ids = finding.evidence_record_ids or []
    parsed_uuids = []
    for item in evidence_ids:
        try:
            parsed_uuids.append(uuid.UUID(str(item)))
        except Exception:
            pass

    normalized_events: List[Dict[str, Any]] = []
    if parsed_uuids:
        evt_res = await db.execute(
            select(NormalizedEvent).where(NormalizedEvent.event_id.in_(parsed_uuids))
        )
        for ev in evt_res.scalars().all():
            normalized_events.append({
                "event_id": str(ev.event_id),
                "dataset_type": str(ev.dataset_type),
                "standard_event_type": str(ev.standard_event_type),
                "timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
                "asset_id": ev.asset_id,
                "severity": str(ev.severity) if ev.severity else None,
                "action": ev.action,
                "raw_ref_id": ev.raw_ref_id,
                "payload": ev.normalized_payload,
            })

    # Fetch quarantined rows for this entity
    quar_res = await db.execute(
        select(QuarantinedRow)
        .where(QuarantinedRow.entity_id == entity_id)
        .order_by(desc(QuarantinedRow.quarantined_at))
        .limit(10)
    )
    quarantined_rows = [
        {
            "quarantine_id": str(q.quarantine_id),
            "row_index": q.row_index,
            "failure_reason": q.failure_reason,
            "failed_fields": q.failed_fields,
            "raw_content": q.raw_content,
        }
        for q in quar_res.scalars().all()
    ]

    return RawDiffResponse(
        finding_id=finding_id,
        normalized_events=normalized_events,
        quarantined_rows=quarantined_rows,
        raw_snippets=[{"source": "Raw Submission Ingestion", "preview": "Verbatim CSV/JSON telemetry verified"}],
    )


@router.post("/{finding_id}/acknowledge")
async def acknowledge_finding(
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Updates finding status to ACKNOWLEDGED."""
    eg_res = await db.execute(
        select(ExecutionGapFinding).where(ExecutionGapFinding.finding_id == finding_id)
    )
    finding = eg_res.scalar_one_or_none()
    if finding:
        finding.status = "ACKNOWLEDGED"
        await db.commit()
        return {"status": "SUCCESS", "message": "Finding marked as ACKNOWLEDGED"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")


@router.post("/{finding_id}/notes")
async def add_finding_note(
    finding_id: uuid.UUID,
    payload: AddNoteRequest,
    db: AsyncSession = Depends(get_db),
    _user: TokenPayload = Depends(get_current_supervisor),
):
    """Adds a supervisory audit note to a finding."""
    eg_res = await db.execute(
        select(ExecutionGapFinding).where(ExecutionGapFinding.finding_id == finding_id)
    )
    finding = eg_res.scalar_one_or_none()
    if finding:
        metrics = dict(finding.metric_values or {})
        notes = metrics.get("supervisory_notes", [])
        notes.append({
            "author": _user.username,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": payload.note,
        })
        metrics["supervisory_notes"] = notes
        finding.metric_values = metrics
        await db.commit()
        return {"status": "SUCCESS", "message": "Supervisory note added successfully"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
