"""Extractor for the 5 benchmarked supervisory cybersecurity metrics."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from ..execution_gap.interpreter import LogicInterpreter
from .models import EntityMetricSnapshot


def extract_entity_metrics(
    entity_id: uuid.UUID,
    sector: str,
    size_tier: str,
    events: List[Any],
    execution_gap_findings: Optional[List[Any]] = None,
) -> EntityMetricSnapshot:
    """
    Computes the 5 supervisory metrics:
    1. MTTI (minutes): Mean time to investigate alerts.
    2. Escalation Rate: Escalations / Alerts.
    3. Stale Case Ratio: Stale (>72h) Cases / Total Cases.
    4. Crown Jewel Coverage Gap: Unmonitored Crown Jewels / Total Crown Jewels.
    5. Execution Gap Rate: EG Findings / Cases * 100.
    """
    events_by_type = defaultdict(list)
    for ev in events:
        ds = str(LogicInterpreter.extract_field_value(ev, "dataset_type") or "")
        std = str(LogicInterpreter.extract_field_value(ev, "standard_event_type") or "")
        events_by_type[ds].append(ev)
        events_by_type[std].append(ev)

    alerts = events_by_type.get("alert_metadata", []) or events_by_type.get("ALERT", [])
    cases = events_by_type.get("case_management", []) or events_by_type.get("CASE", [])
    investigations = events_by_type.get("investigation_records", []) or events_by_type.get("INVESTIGATION", [])
    escalations = events_by_type.get("escalation_records", []) or events_by_type.get("ESCALATION", [])
    assets = events_by_type.get("asset_inventory", []) or events_by_type.get("ASSET", [])
    coverages = events_by_type.get("coverage_reports", []) or events_by_type.get("COVERAGE", [])

    # 1. MTTI Calculation
    # Map investigations by alert_id or case_id
    inv_times = defaultdict(list)
    for inv in investigations:
        itime = LogicInterpreter.extract_field_value(inv, "event_timestamp")
        aid = LogicInterpreter.extract_field_value(inv, "alert_id") or LogicInterpreter.extract_field_value(inv, "raw_ref_id")
        cid = LogicInterpreter.extract_field_value(inv, "case_id")
        if itime:
            if aid:
                inv_times[str(aid)].append(itime)
            if cid:
                inv_times[str(cid)].append(itime)

    mtti_deltas = []
    for a in alerts:
        atime = LogicInterpreter.extract_field_value(a, "event_timestamp")
        aid = LogicInterpreter.extract_field_value(a, "raw_ref_id") or LogicInterpreter.extract_field_value(a, "alert_id")
        if atime and aid and str(aid) in inv_times:
            first_inv = min(inv_times[str(aid)])
            delta_mins = max(0.0, (first_inv - atime).total_seconds() / 60.0)
            mtti_deltas.append(delta_mins)

    # Fallback to time_spent_minutes if direct delta is unavailable
    if not mtti_deltas and investigations:
        for inv in investigations:
            mins = LogicInterpreter.extract_field_value(inv, "time_spent_minutes")
            if mins is not None:
                try:
                    mtti_deltas.append(float(mins))
                except (ValueError, TypeError):
                    pass

    mtti_val = float(sum(mtti_deltas) / len(mtti_deltas)) if mtti_deltas else 45.0

    # 2. Escalation Rate
    total_alerts = max(len(alerts), 1)
    total_escalations = len(escalations)
    escalation_rate = round(float(total_escalations) / float(total_alerts), 4)

    # 3. Stale Case Ratio
    total_cases = len(cases)
    stale_cases = 0
    now = datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None)
    for c in cases:
        st = str(LogicInterpreter.extract_field_value(c, "status") or "").upper()
        if st in ("OPEN", "IN_PROGRESS", "ACTIVE"):
            t = LogicInterpreter.extract_field_value(c, "event_timestamp")
            if t:
                try:
                    # Make tz-aware if needed
                    diff_hours = (now - t).total_seconds() / 3600.0 if t.tzinfo else 75.0
                except TypeError:
                    diff_hours = 75.0
                if diff_hours > 72.0:
                    stale_cases += 1
            else:
                stale_cases += 1

    stale_case_ratio = round(float(stale_cases) / float(max(total_cases, 1)), 4)

    # 4. Crown Jewel Coverage Gap
    crown_jewels = []
    for a in assets:
        crit = str(LogicInterpreter.extract_field_value(a, "criticality_tier") or "").upper()
        if crit in ("CROWN_JEWEL", "CRITICAL", "TIER_1"):
            crown_jewels.append(a)

    total_cj = len(crown_jewels)
    covered_assets = {
        str(LogicInterpreter.extract_field_value(cov, "asset_id") or LogicInterpreter.extract_field_value(cov, "raw_ref_id"))
        for cov in coverages
        if (LogicInterpreter.extract_field_value(cov, "uptime_pct") or 100.0) >= 50.0
    }

    unmonitored_cj = 0
    for cj in crown_jewels:
        aid = LogicInterpreter.extract_field_value(cj, "asset_id") or LogicInterpreter.extract_field_value(cj, "raw_ref_id")
        host = LogicInterpreter.extract_field_value(cj, "hostname")
        if str(aid) not in covered_assets and str(host) not in covered_assets:
            unmonitored_cj += 1

    coverage_gap_ratio = round(float(unmonitored_cj) / float(max(total_cj, 1)), 4)

    # 5. Execution Gap Rate
    eg_count = len(execution_gap_findings) if execution_gap_findings else 0
    eg_rate = round((float(eg_count) / float(max(total_cases, 1))) * 100.0, 2)

    return EntityMetricSnapshot(
        entity_id=entity_id,
        sector=sector,
        size_tier=size_tier,
        mtti_minutes=round(mtti_val, 2),
        escalation_rate=escalation_rate,
        stale_case_ratio=stale_case_ratio,
        coverage_gap_ratio=coverage_gap_ratio,
        execution_gap_rate=eg_rate,
        total_alerts=len(alerts),
        total_cases=total_cases,
        total_crown_jewels=total_cj,
    )
