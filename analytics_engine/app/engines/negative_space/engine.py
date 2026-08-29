"""Negative Space Engine implementation with statistical models and degradation."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
import uuid

from shared.logging import logger
from .models import (
    CheckDefinition,
    NegativeSpaceFindingDraft,
)
from .registry import NegativeSpaceCheckRegistry
from .stats import (
    compute_ewma_baseline,
    compute_inter_arrival_cv,
    compute_low_volume_degradation,
    compute_shannon_entropy,
    detect_ewma_volume_cliff,
)
from ..execution_gap.interpreter import LogicInterpreter


class NegativeSpaceEngine:
    """Evaluates omissions, missing records, and statistical anomalies."""

    def __init__(self, registry: Optional[NegativeSpaceCheckRegistry] = None):
        self.registry = registry or NegativeSpaceCheckRegistry()

    def run(
        self,
        events: List[Any],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """
        Executes all active Negative Space checks against normalized events.
        """
        findings: List[NegativeSpaceFindingDraft] = []
        valid_events = [e for e in (events or []) if e is not None and (isinstance(e, dict) or hasattr(e, "__dict__"))]
        if not valid_events:
            return findings

        # Group events by dataset_type / standard_event_type
        events_by_dataset: Dict[str, List[Any]] = defaultdict(list)
        for ev in valid_events:
            ds_type = getattr(ev, "dataset_type", None) or LogicInterpreter.extract_field_value(ev, "dataset_type")
            std_type = getattr(ev, "standard_event_type", None) or LogicInterpreter.extract_field_value(ev, "standard_event_type")
            if ds_type:
                events_by_dataset[str(ds_type)].append(ev)
                events_by_dataset[str(ds_type).lower()].append(ev)
            if std_type:
                events_by_dataset[str(std_type)].append(ev)
                events_by_dataset[str(std_type).lower()].append(ev)

        for check in self.registry.list_checks(active_only=True):
            try:
                check_findings = self._evaluate_check(
                    check=check,
                    events=events,
                    events_by_dataset=events_by_dataset,
                    entity_id=entity_id,
                    period_start=period_start,
                    period_end=period_end,
                )
                findings.extend(check_findings)
            except Exception as exc:
                logger.error(f"Error evaluating Negative Space check {check.check_id}: {exc}", exc_info=True)

        logger.info(f"Negative Space Engine evaluated {len(findings)} findings for entity {entity_id}")
        return findings

    def _evaluate_check(
        self,
        check: CheckDefinition,
        events: List[Any],
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """Dispatches check evaluation."""
        if check.check_id == "NS-01":
            return self._eval_ns_01(check, events, entity_id, period_start, period_end)
        elif check.check_id == "NS-02":
            return self._eval_ns_02(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-03":
            return self._eval_ns_03(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-04":
            return self._eval_ns_04(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-05":
            return self._eval_ns_05(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-06":
            return self._eval_ns_06(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-07":
            return self._eval_ns_07(check, events_by_dataset, entity_id, period_start, period_end)
        elif check.check_id == "NS-08":
            return self._eval_ns_08(check, events_by_dataset, entity_id, period_start, period_end)
        return []

    # -------------------------------------------------------------------------
    # The 8 MVP Negative Space Checks
    # -------------------------------------------------------------------------

    def _eval_ns_01(
        self,
        check: CheckDefinition,
        events: List[Any],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-01: EWMA Volume Cliff / Sudden Sensor Silence."""
        findings = []
        # Group daily volumes
        daily_counts = defaultdict(int)
        event_ids_by_day = defaultdict(list)

        for ev in events:
            t = LogicInterpreter.extract_field_value(ev, "event_timestamp")
            if t:
                day_key = t.strftime("%Y-%m-%d")
                daily_counts[day_key] += 1
                eid = LogicInterpreter.extract_field_value(ev, "event_id")
                if eid:
                    event_ids_by_day[day_key].append(str(eid))

        if not daily_counts:
            return findings

        sorted_days = sorted(daily_counts.keys())
        volumes = [float(daily_counts[d]) for d in sorted_days]

        cliff_result = detect_ewma_volume_cliff(volumes, alpha=0.20, k=3.0, min_history_days=5)

        if cliff_result:
            sample_n = len(events)
            w_deg, is_deg = compute_low_volume_degradation(sample_n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"Daily telemetry volume dropped from expected baseline of {cliff_result['expected_volume']} "
                f"to {cliff_result['observed_volume']} ({cliff_result['drop_percentage']}% reduction, "
                f"exceeding 3-sigma cliff threshold of {cliff_result['cliff_threshold']})."
            )
            if is_deg:
                rationale += f" [LOW SAMPLE WARNING: Based on N={sample_n} events, baseline confidence dampened]."

            latest_day = sorted_days[-1]
            evidence_ids = event_ids_by_day.get(latest_day, [])[:20]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=cliff_result["expected_volume"],
                observed_volume=cliff_result["observed_volume"],
                drop_percentage=cliff_result["drop_percentage"],
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_02(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-02: Missing Weekend / Off-Hours Analyst Activity (Weekend alerts >= 20, activity == 0)."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        activities = events_by_dataset.get("analyst_activity", []) or events_by_dataset.get("ACTIVITY", [])

        weekend_alerts = []
        for a in alerts:
            t = LogicInterpreter.extract_field_value(a, "event_timestamp")
            if t and t.weekday() in (5, 6):
                weekend_alerts.append(a)

        weekend_activities = []
        for act in activities:
            t = LogicInterpreter.extract_field_value(act, "event_timestamp")
            if t and t.weekday() in (5, 6):
                weekend_activities.append(act)

        observed_alerts = len(weekend_alerts)
        observed_activities = len(weekend_activities)

        if observed_alerts >= 20 and observed_activities == 0:
            sample_n = observed_alerts
            w_deg, is_deg = compute_low_volume_degradation(sample_n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"During weekend evaluation period, {observed_alerts} security alerts fired with "
                f"0 analyst console activity or triage audit logs."
            )
            if is_deg:
                rationale += f" [LOW SAMPLE WARNING: Based on N={sample_n} events, baseline confidence dampened]."

            evidence_ids = [str(LogicInterpreter.extract_field_value(a, "event_id")) for a in weekend_alerts[:20] if LogicInterpreter.extract_field_value(a, "event_id")]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=float(observed_alerts),
                observed_volume=0.0,
                drop_percentage=100.0,
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_03(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-03: Zero Telemetry / Coverage on Crown-Jewel & Tier-1 Assets."""
        findings = []
        assets = events_by_dataset.get("asset_inventory", []) or events_by_dataset.get("ASSET", [])
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        coverages = events_by_dataset.get("coverage_reports", []) or events_by_dataset.get("COVERAGE", [])

        crown_jewels = []
        for a in assets:
            crit = str(LogicInterpreter.extract_field_value(a, "criticality_tier") or "").upper()
            if crit in ("CROWN_JEWEL", "CRITICAL", "TIER_1", "TIER-1"):
                crown_jewels.append(a)

        if not crown_jewels:
            return findings

        # Index alerts & coverages by asset_id
        telemetry_assets = set()
        for cov in coverages:
            aid = LogicInterpreter.extract_field_value(cov, "asset_id") or LogicInterpreter.extract_field_value(cov, "raw_ref_id")
            if aid:
                telemetry_assets.add(str(aid))

        for alt in alerts:
            aid = LogicInterpreter.extract_field_value(alt, "asset_id")
            if aid:
                telemetry_assets.add(str(aid))

        unmonitored_assets = []
        for cj in crown_jewels:
            aid = LogicInterpreter.extract_field_value(cj, "asset_id") or LogicInterpreter.extract_field_value(cj, "raw_ref_id")
            host = LogicInterpreter.extract_field_value(cj, "hostname")
            if str(aid) not in telemetry_assets and (not host or str(host) not in telemetry_assets):
                unmonitored_assets.append(cj)

        if unmonitored_assets:
            total_cj = len(crown_jewels)
            unmon_count = len(unmonitored_assets)
            drop_pct = round((unmon_count / float(total_cj)) * 100.0, 1)

            sev_score = check.severity_base
            evidence_ids = [str(LogicInterpreter.extract_field_value(a, "event_id")) for a in unmonitored_assets if LogicInterpreter.extract_field_value(a, "event_id")]
            asset_refs = [str(LogicInterpreter.extract_field_value(a, "asset_id") or LogicInterpreter.extract_field_value(a, "hostname")) for a in unmonitored_assets]

            rationale = f"{unmon_count} out of {total_cj} Tier-1 Critical assets ({', '.join(asset_refs[:5])}) exhibit total telemetry silence and lack active EDR/WAF/NDR logs."

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity="CRITICAL",
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=float(total_cj),
                observed_volume=float(total_cj - unmon_count),
                drop_percentage=drop_pct,
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                raw_evidence_refs=asset_refs,
                metric_values={"unmonitored_count": unmon_count, "total_critical_assets": total_cj},
                is_degraded=False,
                degradation_factor=1.0,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_04(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-04: Asymmetric Case Closure vs Creation Rate (Created >= 30, Closure < 10%)."""
        findings = []
        cases = events_by_dataset.get("case_management", []) or events_by_dataset.get("CASE", [])

        if len(cases) < 30:
            return findings

        created_count = len(cases)
        closed_count = 0
        for c in cases:
            st = str(LogicInterpreter.extract_field_value(c, "status") or "").upper()
            if st in ("CLOSED", "RESOLVED"):
                closed_count += 1

        closure_rate = round((closed_count / float(created_count)) * 100.0, 1)

        if closure_rate < 10.0:
            sample_n = created_count
            w_deg, is_deg = compute_low_volume_degradation(sample_n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"Over the evaluation period, {created_count} cases were opened but only {closed_count} "
                f"were resolved (closure rate {closure_rate}% < 10% threshold)."
            )
            if is_deg:
                rationale += f" [LOW SAMPLE WARNING: Based on N={sample_n} events, baseline confidence dampened]."

            evidence_ids = [str(LogicInterpreter.extract_field_value(c, "event_id")) for c in cases[:20] if LogicInterpreter.extract_field_value(c, "event_id")]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=float(created_count),
                observed_volume=float(closed_count),
                drop_percentage=round(100.0 - closure_rate, 1),
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_05(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-05: Missing Escalations on High-Severity Alert Spike (>=20 high/critical alerts, 0 escalations)."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])
        escalations = events_by_dataset.get("escalation_records", []) or events_by_dataset.get("ESCALATION", [])

        high_crit_alerts = []
        for a in alerts:
            sev = str(LogicInterpreter.extract_field_value(a, "severity") or "").upper()
            if sev in ("CRITICAL", "HIGH"):
                high_crit_alerts.append(a)

        observed_count = len(high_crit_alerts)
        esc_count = len(escalations)

        if observed_count >= 20 and esc_count == 0:
            sample_n = observed_count
            w_deg, is_deg = compute_low_volume_degradation(sample_n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"A surge of {observed_count} High/Critical priority alerts occurred during the evaluation window "
                f"with zero escalations to Tier-2/Tier-3 IR teams."
            )
            if is_deg:
                rationale += f" [LOW SAMPLE WARNING: Based on N={sample_n} events, baseline confidence dampened]."

            evidence_ids = [str(LogicInterpreter.extract_field_value(a, "event_id")) for a in high_crit_alerts[:20] if LogicInterpreter.extract_field_value(a, "event_id")]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=float(observed_count),
                observed_volume=0.0,
                drop_percentage=100.0,
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_06(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-06: Low Categorical Shannon Entropy (Monoculture / Blinded Rules: H(X) < 0.50 with N >= 50)."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])

        if len(alerts) < 50:
            return findings

        categories = []
        for a in alerts:
            cat = LogicInterpreter.extract_field_value(a, "rule_id") or LogicInterpreter.extract_field_value(a, "alert_name") or LogicInterpreter.extract_field_value(a, "action")
            if cat:
                categories.append(str(cat))

        if len(categories) < 50:
            return findings

        entropy, max_h, n, m = compute_shannon_entropy(categories)

        if entropy < 0.50:
            w_deg, is_deg = compute_low_volume_degradation(n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"Categorical alert rule distribution exhibits abnormally low Shannon entropy H(X) = {entropy} bits "
                f"(< 0.50 bits threshold across N={n} alerts and M={m} rules), indicating sensor blindness on other attack vectors."
            )
            evidence_ids = [str(LogicInterpreter.extract_field_value(a, "event_id")) for a in alerts[:20] if LogicInterpreter.extract_field_value(a, "event_id")]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=max_h,
                observed_volume=entropy,
                drop_percentage=round((1.0 - (entropy / max(0.1, max_h))) * 100.0, 1),
                entropy_score=entropy,
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_07(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-07: Unnaturally Constant Alert Intervals (CV < 0.01 with N >= 20)."""
        findings = []
        alerts = events_by_dataset.get("alert_metadata", []) or events_by_dataset.get("ALERT", [])

        if len(alerts) < 20:
            return findings

        timestamps = []
        for a in alerts:
            t = LogicInterpreter.extract_field_value(a, "event_timestamp")
            if t:
                timestamps.append(t)

        if len(timestamps) < 20:
            return findings

        cv, mu_delta, sigma_delta, n = compute_inter_arrival_cv(timestamps)

        if cv < 0.01:
            w_deg, is_deg = compute_low_volume_degradation(n, n_min=check.min_sample_size)
            sev_score = int(round(check.severity_base * w_deg))

            rationale = (
                f"Alert inter-arrival times exhibit near-zero variance (CV = {cv} < 0.01 threshold, "
                f"mean delta {mu_delta}s, sigma {sigma_delta}s across N={n} alerts), indicating synthetic heartbeat or mock telemetry."
            )
            evidence_ids = [str(LogicInterpreter.extract_field_value(a, "event_id")) for a in alerts[:20] if LogicInterpreter.extract_field_value(a, "event_id")]

            draft = NegativeSpaceFindingDraft(
                entity_id=entity_id,
                check_id=check.check_id,
                check_name=check.name,
                check_category=check.category,
                severity=self._score_to_severity_tier(sev_score),
                severity_score=sev_score,
                confidence=check.confidence,
                period_start=period_start,
                period_end=period_end,
                expected_volume=1.0,
                observed_volume=cv,
                drop_percentage=round((1.0 - cv) * 100.0, 1),
                rationale=rationale,
                evidence_record_ids=evidence_ids,
                is_degraded=is_deg,
                degradation_factor=w_deg,
                recommendation=check.recommendation,
            )
            findings.append(draft)

        return findings

    def _eval_ns_08(
        self,
        check: CheckDefinition,
        events_by_dataset: Dict[str, List[Any]],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> List[NegativeSpaceFindingDraft]:
        """NS-08: Missing Post-Incident Remediation / Audit Trace (>14 days resolved)."""
        findings = []
        incidents = events_by_dataset.get("incident_reports", []) or events_by_dataset.get("INCIDENT", [])
        coverages = events_by_dataset.get("coverage_reports", []) or events_by_dataset.get("COVERAGE", [])
        activities = events_by_dataset.get("analyst_activity", []) or events_by_dataset.get("ACTIVITY", [])

        for inc in incidents:
            resolved_at = LogicInterpreter.extract_field_value(inc, "resolved_at")
            inc_time = LogicInterpreter.extract_field_value(inc, "event_timestamp") or LogicInterpreter.extract_field_value(inc, "declared_at")
            res_t = resolved_at or inc_time

            if not res_t:
                continue

            days_since = (period_end - res_t).total_seconds() / 86400.0
            if days_since > 14.0:
                # Check for post-incident activity/coverage updates after res_t
                has_post_updates = False
                for item in coverages + activities:
                    t = LogicInterpreter.extract_field_value(item, "event_timestamp")
                    if t and t > res_t:
                        has_post_updates = True
                        break

                if not has_post_updates:
                    inc_id = LogicInterpreter.extract_field_value(inc, "raw_ref_id") or LogicInterpreter.extract_field_value(inc, "incident_id") or "Incident"
                    event_uuid = str(LogicInterpreter.extract_field_value(inc, "event_id") or inc_id)

                    sev_score = check.severity_base
                    rationale = (
                        f"Critical security incident {inc_id} was resolved {int(days_since)} days ago "
                        f"without subsequent coverage telemetry updates or post-incident audit reviews."
                    )

                    draft = NegativeSpaceFindingDraft(
                        entity_id=entity_id,
                        check_id=check.check_id,
                        check_name=check.name,
                        check_category=check.category,
                        severity="MEDIUM",
                        severity_score=sev_score,
                        confidence=check.confidence,
                        period_start=period_start,
                        period_end=period_end,
                        expected_volume=1.0,
                        observed_volume=0.0,
                        drop_percentage=100.0,
                        rationale=rationale,
                        evidence_record_ids=[event_uuid],
                        is_degraded=False,
                        degradation_factor=1.0,
                        recommendation=check.recommendation,
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
