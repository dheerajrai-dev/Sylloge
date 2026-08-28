"""Execution Gap Engine implementation with AST evaluation."""

from collections import defaultdict
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid

from shared.events.enums import DatasetType, SeverityTier, StandardEventType
from shared.logging import logger
from .interpreter import LogicInterpreter
from .models import (
    ConditionOperator,
    ExecutionGapFindingDraft,
    JoinRelation,
    RuleDefinition,
)
from .registry import ExecutionGapRuleRegistry


class ExecutionGapEngine:
    """Evaluates compliance execution gaps across normalized event streams."""

    def __init__(self, registry: Optional[ExecutionGapRuleRegistry] = None):
        self.registry = registry or ExecutionGapRuleRegistry()

    def run(
        self,
        events: List[Any],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """
        Executes all active Execution Gap rules against the provided normalized events.
        """
        findings: List[ExecutionGapFindingDraft] = []
        valid_events = [e for e in (events or []) if e is not None and (isinstance(e, dict) or hasattr(e, "__dict__"))]
        if not valid_events:
            return findings

        # Group events by dataset_type / standard_event_type for efficient lookups
        events_by_dataset: Dict[str, List[Any]] = defaultdict(list)
        for ev in valid_events:
            ds_type = LogicInterpreter.extract_field_value(ev, "dataset_type")
            std_type = LogicInterpreter.extract_field_value(ev, "standard_event_type")
            if ds_type:
                events_by_dataset[str(ds_type)].append(ev)
            if std_type:
                events_by_dataset[str(std_type)].append(ev)

        # Iterate through active rules in registry
        for rule in self.registry.list_rules(active_only=True):
            try:
                rule_findings = self._evaluate_rule(
                    rule=rule,
                    events=events,
                    events_by_dataset=events_by_dataset,
                    entity_id=entity_id,
                    period_start=period_start,
                    period_end=period_end,
                )
                findings.extend(rule_findings)
            except Exception as exc:
                logger.error(f"Error evaluating rule {rule.rule_code}: {exc}", exc_info=True)

        logger.info(f"Execution Gap Engine evaluated {len(findings)} findings for entity {entity_id}")
        return findings

    def _evaluate_rule(
        self,
        rule: RuleDefinition,
        events: List[Any],
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """Dispatches rule evaluation to specialized handler or generic interpreter."""
        if rule.rule_code == "EG-01":
            return self._eval_eg_01(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-02":
            return self._eval_eg_02(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-03":
            return self._eval_eg_03(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-04":
            return self._eval_eg_04(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-05":
            return self._eval_eg_05(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-06":
            return self._eval_eg_06(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-07":
            return self._eval_eg_07(rule, events_by_dataset, entity_id, period_start, period_end)
        elif rule.rule_code == "EG-08":
            return self._eval_eg_08(rule, events_by_dataset, entity_id, period_start, period_end)
        else:
            return self._eval_generic_rule(rule, events_by_dataset, entity_id, period_start, period_end)

    # -------------------------------------------------------------------------
    # Specialized 8 MVP Rule Evaluators
    # -------------------------------------------------------------------------

    def _eval_eg_01(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-01: Uninvestigated Critical / High Alerts."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        investigations = events_by_dataset.get("investigation_records", []) or events_by_dataset.get("INVESTIGATION", [])

        # Index investigations by alert_id and case_id
        inv_by_ref = defaultdict(list)
        for inv in investigations:
            inv_time = LogicInterpreter.extract_field_value(inv, "event_timestamp")
            ref_id = LogicInterpreter.extract_field_value(inv, "raw_ref_id")
            case_id = LogicInterpreter.extract_field_value(inv, "case_id")
            alert_id = LogicInterpreter.extract_field_value(inv, "alert_id")
            for k in filter(None, [ref_id, case_id, alert_id]):
                inv_by_ref[str(k)].append(inv_time)

        for alert in alerts:
            severity = str(LogicInterpreter.extract_field_value(alert, "severity") or "").upper()
            if severity not in ("CRITICAL", "HIGH"):
                continue

            alert_id = LogicInterpreter.extract_field_value(alert, "raw_ref_id") or LogicInterpreter.extract_field_value(alert, "alert_id")
            case_id = LogicInterpreter.extract_field_value(alert, "case_id")
            alert_name = LogicInterpreter.extract_field_value(alert, "alert_name") or LogicInterpreter.extract_field_value(alert, "action") or "Security Alert"
            asset_id = LogicInterpreter.extract_field_value(alert, "asset_id") or "Unknown Asset"
            alert_time = LogicInterpreter.extract_field_value(alert, "event_timestamp")

            # Check if investigated within 2 hours
            has_investigation = False
            for k in filter(None, [alert_id, case_id]):
                for itime in inv_by_ref.get(str(k), []):
                    if alert_time and itime:
                        delta = (itime - alert_time).total_seconds()
                        if 0 <= delta <= 7200:
                            has_investigation = True
                            break
                    else:
                        has_investigation = True
                        break
                if has_investigation:
                    break

            if not has_investigation:
                # Calculate delay hours
                delay_hours = 2.0
                if alert_time:
                    delay_hours = max(2.0, (period_end - alert_time).total_seconds() / 3600.0)

                sev_score = min(100, int(70 + 5 * math.floor(delay_hours)))
                event_uuid = str(LogicInterpreter.extract_field_value(alert, "event_id") or alert_id)
                raw_idx = LogicInterpreter.extract_field_value(alert, "raw_row_index")

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity=self._score_to_severity_tier(sev_score),
                    severity_score=sev_score,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"Critical or High severity alert {alert_id} ({alert_name}) uninvestigated after 2-hour SLA.",
                    rationale=f"Alert {alert_id} ({alert_name}) on asset {asset_id} with severity {severity} received no investigation within the 2-hour SLA window.",
                    evidence_record_ids=[event_uuid],
                    raw_evidence_refs=[alert_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"delay_hours": round(delay_hours, 1), "sla_threshold_hours": 2},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    def _eval_eg_02(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-02: Missing Escalation After Severity Threshold."""
        findings = []
        cases = events_by_dataset.get("case_management", []) or events_by_dataset.get("CASE", [])
        escalations = events_by_dataset.get("escalation_records", []) or events_by_dataset.get("ESCALATION", [])

        escalated_case_ids = set()
        for esc in escalations:
            cid = LogicInterpreter.extract_field_value(esc, "case_id") or LogicInterpreter.extract_field_value(esc, "raw_ref_id")
            if cid:
                escalated_case_ids.add(str(cid))

        for case in cases:
            priority = str(LogicInterpreter.extract_field_value(case, "priority") or "").upper()
            severity = str(LogicInterpreter.extract_field_value(case, "severity") or "").upper()
            if not ("P1" in priority or "CRITICAL" in priority or severity == "CRITICAL"):
                continue

            case_id = LogicInterpreter.extract_field_value(case, "raw_ref_id") or LogicInterpreter.extract_field_value(case, "case_id")
            if not case_id or str(case_id) in escalated_case_ids:
                continue

            created_time = LogicInterpreter.extract_field_value(case, "event_timestamp")
            closed_time = LogicInterpreter.extract_field_value(case, "closed_at")

            duration_open = 5.0
            if created_time:
                end_t = closed_time or period_end
                duration_open = max(0.0, (end_t - created_time).total_seconds() / 3600.0)

            if duration_open >= 4.0:
                event_uuid = str(LogicInterpreter.extract_field_value(case, "event_id") or case_id)
                raw_idx = LogicInterpreter.extract_field_value(case, "raw_row_index")

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity="CRITICAL",
                    severity_score=rule.severity_base,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"P1 Critical Case {case_id} remained unescalated beyond 4-hour SLA.",
                    rationale=f"P1 Critical Case {case_id} remained unescalated after {round(duration_open, 1)} hours of active status.",
                    evidence_record_ids=[event_uuid],
                    raw_evidence_refs=[case_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"duration_open_hours": round(duration_open, 1), "sla_threshold_hours": 4},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    def _eval_eg_03(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-03: Stale Open Cases (> 72 hours)."""
        findings = []
        cases = events_by_dataset.get("case_management", []) or events_by_dataset.get("CASE", [])
        activities = events_by_dataset.get("analyst_activity", []) or events_by_dataset.get("ACTIVITY", [])
        investigations = events_by_dataset.get("investigation_records", []) or events_by_dataset.get("INVESTIGATION", [])

        # Map last activity/investigation time per case
        last_action_by_case: Dict[str, datetime] = {}
        for item in activities + investigations:
            cid = LogicInterpreter.extract_field_value(item, "case_id")
            itime = LogicInterpreter.extract_field_value(item, "event_timestamp")
            if cid and itime:
                cid_str = str(cid)
                if cid_str not in last_action_by_case or itime > last_action_by_case[cid_str]:
                    last_action_by_case[cid_str] = itime

        for case in cases:
            status = str(LogicInterpreter.extract_field_value(case, "status") or "").upper()
            if status not in ("OPEN", "IN_PROGRESS", "ACTIVE", "NEW"):
                continue

            case_id = LogicInterpreter.extract_field_value(case, "raw_ref_id") or LogicInterpreter.extract_field_value(case, "case_id")
            created_time = LogicInterpreter.extract_field_value(case, "event_timestamp")

            last_action = last_action_by_case.get(str(case_id)) or created_time or period_start
            idle_hours = max(0.0, (period_end - last_action).total_seconds() / 3600.0)

            if idle_hours > 72.0:
                idle_days = round(idle_hours / 24.0, 1)
                sev_score = min(100, int(50 + 5 * math.floor((idle_hours - 72) / 24)))
                event_uuid = str(LogicInterpreter.extract_field_value(case, "event_id") or case_id)
                raw_idx = LogicInterpreter.extract_field_value(case, "raw_row_index")

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity=self._score_to_severity_tier(sev_score),
                    severity_score=sev_score,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"Case {case_id} has been dormant for over 72 hours without analyst activity.",
                    rationale=f"Case {case_id} has been dormant for {idle_days} days without any analyst audit trail or notes.",
                    evidence_record_ids=[event_uuid],
                    raw_evidence_refs=[case_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"idle_hours": round(idle_hours, 1), "idle_days": idle_days, "threshold_hours": 72},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    def _eval_eg_04(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-04: Case Closure Without Resolution Notes."""
        findings = []
        cases = events_by_dataset.get("case_management", []) or events_by_dataset.get("CASE", [])
        investigations = events_by_dataset.get("investigation_records", []) or events_by_dataset.get("INVESTIGATION", [])

        # Map investigation notes by case_id
        notes_by_case = defaultdict(list)
        inv_events_by_case = defaultdict(list)
        for inv in investigations:
            cid = LogicInterpreter.extract_field_value(inv, "case_id") or LogicInterpreter.extract_field_value(inv, "raw_ref_id")
            notes = LogicInterpreter.extract_field_value(inv, "investigation_notes") or LogicInterpreter.extract_field_value(inv, "conclusion")
            if cid:
                if notes:
                    notes_by_case[str(cid)].append(str(notes))
                inv_events_by_case[str(cid)].append(inv)

        generic_words = {"closed", "done", "fp", "resolved", "n/a", "na", "false positive", "ok", "fine", "none"}

        for case in cases:
            status = str(LogicInterpreter.extract_field_value(case, "status") or "").upper()
            if status not in ("CLOSED", "RESOLVED"):
                continue

            case_id = LogicInterpreter.extract_field_value(case, "raw_ref_id") or LogicInterpreter.extract_field_value(case, "case_id")
            case_notes = LogicInterpreter.extract_field_value(case, "notes") or LogicInterpreter.extract_field_value(case, "resolution_notes")
            
            all_notes = notes_by_case.get(str(case_id), [])
            if case_notes:
                all_notes.append(str(case_notes))

            is_non_diligent = False
            note_sample = ""

            if not all_notes:
                is_non_diligent = True
                note_sample = "[NO NOTES RECORDED]"
            else:
                combined_notes = " ".join(all_notes).strip()
                note_sample = combined_notes
                if len(combined_notes) < 20 or combined_notes.lower() in generic_words:
                    is_non_diligent = True

            if is_non_diligent:
                event_uuid = str(LogicInterpreter.extract_field_value(case, "event_id") or case_id)
                raw_idx = LogicInterpreter.extract_field_value(case, "raw_row_index")
                
                evidence_ids = [event_uuid]
                for inv in inv_events_by_case.get(str(case_id), []):
                    inv_uuid = LogicInterpreter.extract_field_value(inv, "event_id")
                    if inv_uuid:
                        evidence_ids.append(str(inv_uuid))

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity="HIGH",
                    severity_score=rule.severity_base,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"Case {case_id} closed without adequate resolution notes.",
                    rationale=f'Case {case_id} was closed with non-diligent resolution notes ("{note_sample[:60]}").',
                    evidence_record_ids=evidence_ids,
                    raw_evidence_refs=[case_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"notes_length": len(note_sample), "min_required_length": 20},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    def _eval_eg_05(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-05: Unassigned Critical Assets in Alerts."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        assets = events_by_dataset.get("asset_inventory", []) or events_by_dataset.get("ASSET", [])

        # Map asset ownership by asset_id and hostname
        asset_info: Dict[str, Dict[str, Any]] = {}
        for a in assets:
            aid = LogicInterpreter.extract_field_value(a, "asset_id") or LogicInterpreter.extract_field_value(a, "raw_ref_id")
            host = LogicInterpreter.extract_field_value(a, "hostname")
            owner = LogicInterpreter.extract_field_value(a, "owner")
            dept = LogicInterpreter.extract_field_value(a, "department")
            crit = LogicInterpreter.extract_field_value(a, "criticality_tier")

            data = {"owner": owner, "department": dept, "criticality_tier": crit, "hostname": host, "event_id": LogicInterpreter.extract_field_value(a, "event_id")}
            if aid:
                asset_info[str(aid)] = data
            if host:
                asset_info[str(host)] = data

        for alert in alerts:
            asset_id = LogicInterpreter.extract_field_value(alert, "asset_id") or "Unknown"
            crit_alert = LogicInterpreter.extract_field_value(alert, "criticality_tier")

            info = asset_info.get(str(asset_id), {})
            crit_final = str(info.get("criticality_tier") or crit_alert or "").upper()

            if crit_final in ("CROWN_JEWEL", "CRITICAL", "TIER_1"):
                owner = info.get("owner") or LogicInterpreter.extract_field_value(alert, "owner")
                dept = info.get("department") or LogicInterpreter.extract_field_value(alert, "department")

                if not owner or not dept:
                    event_uuid = str(LogicInterpreter.extract_field_value(alert, "event_id") or alert_id)
                    alert_id = LogicInterpreter.extract_field_value(alert, "raw_ref_id") or "Alert"
                    hostname = info.get("hostname") or asset_id
                    raw_idx = LogicInterpreter.extract_field_value(alert, "raw_row_index")

                    evidence_ids = [event_uuid]
                    if info.get("event_id"):
                        evidence_ids.append(str(info["event_id"]))

                    draft = ExecutionGapFindingDraft(
                        entity_id=entity_id,
                        rule_id=rule.rule_code,
                        rule_name=rule.name,
                        rule_category=rule.category,
                        severity="MEDIUM",
                        severity_score=rule.severity_base,
                        confidence=rule.confidence,
                        period_start=period_start,
                        period_end=period_end,
                        description=f"Alert on Crown Jewel asset {asset_id} lacking CMDB ownership.",
                        rationale=f"Crown Jewel asset {hostname} ({asset_id}) triggered critical security alerts but lacks an assigned departmental owner in CMDB.",
                        evidence_record_ids=evidence_ids,
                        raw_evidence_refs=[asset_id, alert_id],
                        raw_row_indices=[raw_idx] if raw_idx is not None else [],
                        metric_values={"criticality_tier": crit_final, "owner": owner or "UNASSIGNED", "department": dept or "UNASSIGNED"},
                        recommendation=rule.recommendation,
                    )
                    findings.append(draft)

        return findings

    def _eval_eg_06(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-06: Escalation Without Incident Record."""
        findings = []
        escalations = events_by_dataset.get("escalation_records", []) or events_by_dataset.get("ESCALATION", [])
        incidents = events_by_dataset.get("incident_reports", []) or events_by_dataset.get("INCIDENT", [])

        # Map incidents by case_id
        incidents_by_case = defaultdict(list)
        for inc in incidents:
            cid = LogicInterpreter.extract_field_value(inc, "case_id") or LogicInterpreter.extract_field_value(inc, "raw_ref_id")
            itime = LogicInterpreter.extract_field_value(inc, "event_timestamp") or LogicInterpreter.extract_field_value(inc, "declared_at")
            if cid:
                incidents_by_case[str(cid)].append(itime)

        for esc in escalations:
            esc_to = str(LogicInterpreter.extract_field_value(esc, "escalated_to") or "").upper()
            if not ("TIER_3" in esc_to or "MANAGEMENT" in esc_to or "CERT" in esc_to or "IR" in esc_to):
                continue

            case_id = LogicInterpreter.extract_field_value(esc, "case_id") or LogicInterpreter.extract_field_value(esc, "raw_ref_id")
            esc_time = LogicInterpreter.extract_field_value(esc, "event_timestamp") or LogicInterpreter.extract_field_value(esc, "escalated_at")

            # Check if incident declared within 24 hours
            has_incident = False
            for itime in incidents_by_case.get(str(case_id), []):
                if esc_time and itime:
                    delta = (itime - esc_time).total_seconds()
                    if 0 <= delta <= 86400:
                        has_incident = True
                        break
                else:
                    has_incident = True
                    break

            if not has_incident and case_id:
                event_uuid = str(LogicInterpreter.extract_field_value(esc, "event_id") or case_id)
                esc_id = LogicInterpreter.extract_field_value(esc, "raw_ref_id") or "Escalation"
                raw_idx = LogicInterpreter.extract_field_value(esc, "raw_row_index")

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity="HIGH",
                    severity_score=rule.severity_base,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"Tier-3 IR escalation for Case {case_id} missing incident declaration report.",
                    rationale=f"Tier-3 IR escalation for Case {case_id} was not followed by a formal incident declaration report within 24 hours.",
                    evidence_record_ids=[event_uuid],
                    raw_evidence_refs=[case_id, esc_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"escalated_to": esc_to, "sla_hours": 24},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    def _eval_eg_07(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-07: Rapid Batch Case Dismissal (Rubber-Stamping: >=10 cases in <= 120 seconds)."""
        findings = []
        cases = events_by_dataset.get("case_management", []) or events_by_dataset.get("CASE", [])
        
        # Group closed/resolved cases by analyst_id
        closed_by_analyst: Dict[str, List[Any]] = defaultdict(list)
        for c in cases:
            status = str(LogicInterpreter.extract_field_value(c, "status") or "").upper()
            if status in ("CLOSED", "RESOLVED"):
                analyst = LogicInterpreter.extract_field_value(c, "user_id") or LogicInterpreter.extract_field_value(c, "assigned_analyst_id") or "Unknown"
                closed_time = LogicInterpreter.extract_field_value(c, "closed_at") or LogicInterpreter.extract_field_value(c, "event_timestamp")
                if closed_time:
                    closed_by_analyst[str(analyst)].append(c)

        for analyst_id, c_list in closed_by_analyst.items():
            if len(c_list) < 10:
                continue

            # Sort by closed_time
            c_list.sort(key=lambda x: (LogicInterpreter.extract_field_value(x, "closed_at") or LogicInterpreter.extract_field_value(x, "event_timestamp")))

            # Sliding window of 10 items
            for i in range(len(c_list) - 9):
                batch = c_list[i : i + 10]
                t_start = LogicInterpreter.extract_field_value(batch[0], "closed_at") or LogicInterpreter.extract_field_value(batch[0], "event_timestamp")
                t_end = LogicInterpreter.extract_field_value(batch[-1], "closed_at") or LogicInterpreter.extract_field_value(batch[-1], "event_timestamp")

                if t_start and t_end:
                    delta_seconds = abs((t_end - t_start).total_seconds())
                    if delta_seconds <= 120.0:
                        evidence_ids = [str(LogicInterpreter.extract_field_value(item, "event_id")) for item in batch if LogicInterpreter.extract_field_value(item, "event_id")]
                        raw_refs = [LogicInterpreter.extract_field_value(item, "raw_ref_id") for item in batch]
                        raw_indices = [LogicInterpreter.extract_field_value(item, "raw_row_index") for item in batch if LogicInterpreter.extract_field_value(item, "raw_row_index") is not None]

                        draft = ExecutionGapFindingDraft(
                            entity_id=entity_id,
                            rule_id=rule.rule_code,
                            rule_name=rule.name,
                            rule_category=rule.category,
                            severity="CRITICAL",
                            severity_score=rule.severity_base,
                            confidence=rule.confidence,
                            period_start=period_start,
                            period_end=period_end,
                            description=f"Analyst {analyst_id} dismissed 10 cases in {int(delta_seconds)} seconds.",
                            rationale=f"Analyst {analyst_id} dismissed 10 cases in {int(delta_seconds)} seconds, indicating systematic rubber-stamping.",
                            evidence_record_ids=evidence_ids,
                            raw_evidence_refs=raw_refs,
                            raw_row_indices=raw_indices,
                            metric_values={"batch_count": 10, "elapsed_seconds": int(delta_seconds), "threshold_seconds": 120},
                            recommendation=rule.recommendation,
                        )
                        findings.append(draft)
                        break  # One finding per burst to avoid redundant overlap

        return findings

    def _eval_eg_08(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """EG-08: Off-Hours Critical Alert SLA Breach (triage delay > 60m)."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        activities = events_by_dataset.get("analyst_activity", []) or events_by_dataset.get("ACTIVITY", [])
        investigations = events_by_dataset.get("investigation_records", []) or events_by_dataset.get("INVESTIGATION", [])

        # Map first action time
        actions_by_alert = defaultdict(list)
        for act in activities + investigations:
            aid = LogicInterpreter.extract_field_value(act, "alert_id") or LogicInterpreter.extract_field_value(act, "raw_ref_id")
            atime = LogicInterpreter.extract_field_value(act, "event_timestamp")
            if aid and atime:
                actions_by_alert[str(aid)].append(atime)

        for alert in alerts:
            severity = str(LogicInterpreter.extract_field_value(alert, "severity") or "").upper()
            if severity not in ("CRITICAL", "HIGH"):
                continue

            alert_time = LogicInterpreter.extract_field_value(alert, "event_timestamp")
            if not alert_time:
                continue

            # Check if off-hours (18:00 - 08:00 UTC or Sat/Sun weekday >= 5)
            is_weekend = alert_time.weekday() in (5, 6)
            is_night = alert_time.hour < 8 or alert_time.hour >= 18
            if not (is_weekend or is_night):
                continue

            alert_id = LogicInterpreter.extract_field_value(alert, "raw_ref_id") or LogicInterpreter.extract_field_value(alert, "alert_id")
            action_times = actions_by_alert.get(str(alert_id), [])

            delay_minutes = 65.0
            if action_times:
                first_action = min(action_times)
                delay_minutes = max(0.0, (first_action - alert_time).total_seconds() / 60.0)
            else:
                delay_minutes = max(60.0, (period_end - alert_time).total_seconds() / 60.0)

            if delay_minutes > 60.0:
                event_uuid = str(LogicInterpreter.extract_field_value(alert, "event_id") or alert_id)
                raw_idx = LogicInterpreter.extract_field_value(alert, "raw_row_index")

                draft = ExecutionGapFindingDraft(
                    entity_id=entity_id,
                    rule_id=rule.rule_code,
                    rule_name=rule.name,
                    rule_category=rule.category,
                    severity="HIGH",
                    severity_score=rule.severity_base,
                    confidence=rule.confidence,
                    period_start=period_start,
                    period_end=period_end,
                    description=f"Off-hours critical alert {alert_id} triage delay breached 60-minute SLA.",
                    rationale=f"Off-hours critical alert {alert_id} experienced triage delay of {int(delay_minutes)} minutes, breaching the 60-minute off-hours SLA.",
                    evidence_record_ids=[event_uuid],
                    raw_evidence_refs=[alert_id],
                    raw_row_indices=[raw_idx] if raw_idx is not None else [],
                    metric_values={"delay_minutes": int(delay_minutes), "sla_threshold_minutes": 60, "is_weekend": is_weekend, "is_night": is_night},
                    recommendation=rule.recommendation,
                )
                findings.append(draft)

        return findings

    # -------------------------------------------------------------------------
    # Generic Declarative Rule Evaluator
    # -------------------------------------------------------------------------

    def _eval_generic_rule(
        self,
        rule: RuleDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[ExecutionGapFindingDraft]:
        """Generic AST evaluator for custom registered execution gap rules."""
        findings = []
        target_events = events_by_dataset.get(rule.target_dataset, [])

        for event in target_events:
            # 1. Filter condition
            if rule.filter_condition and not LogicInterpreter.evaluate_condition(rule.filter_condition, event):
                continue

            # 2. Temporal join condition
            if rule.temporal_join:
                join_targets = events_by_dataset.get(rule.temporal_join.target_dataset, [])
                matched, joined_records = LogicInterpreter.evaluate_temporal_join(
                    rule.temporal_join, event, join_targets
                )
                if not matched:
                    continue

            # 3. Build finding
            event_uuid = str(LogicInterpreter.extract_field_value(event, "event_id") or uuid.uuid4())
            ref_id = LogicInterpreter.extract_field_value(event, "raw_ref_id")
            raw_idx = LogicInterpreter.extract_field_value(event, "raw_row_index")

            # Format rationale and description
            ctx = {"rule_code": rule.rule_code, "name": rule.name, "entity_id": str(entity_id), "ref_id": ref_id}
            desc = rule.description_template.format(**ctx) if "{" in rule.description_template else rule.description_template
            rationale = rule.rationale_template.format(**ctx) if "{" in rule.rationale_template else rule.rationale_template

            draft = ExecutionGapFindingDraft(
                entity_id=entity_id,
                rule_id=rule.rule_code,
                rule_name=rule.name,
                rule_category=rule.category,
                severity=self._score_to_severity_tier(rule.severity_base),
                severity_score=rule.severity_base,
                confidence=rule.confidence,
                period_start=period_start,
                period_end=period_end,
                description=desc,
                rationale=rationale,
                evidence_record_ids=[event_uuid],
                raw_evidence_refs=[ref_id] if ref_id else [],
                raw_row_indices=[raw_idx] if raw_idx is not None else [],
                metric_values={},
                recommendation=rule.recommendation,
            )
            findings.append(draft)

        return findings

    @staticmethod
    def _score_to_severity_tier(score: int) -> str:
        """Maps 0-100 severity score to standardized SeverityTier enum string."""
        if score >= 85:
            return "CRITICAL"
        if score >= 70:
            return "HIGH"
        if score >= 40:
            return "MEDIUM"
        return "LOW"
