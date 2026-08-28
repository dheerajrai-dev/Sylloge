"""Rationale Card builder for explainability."""

from typing import Any, Dict, List, Optional
import uuid

from shared.schemas.finding import RationaleCard
from .models import RationaleCardData


class RationaleCardBuilder:
    """Constructs structured Rationale Cards from engine findings with forensic tracing."""

    @staticmethod
    def build_from_execution_gap(
        finding: Any,
        entity_id: uuid.UUID,
        events_map: Optional[Dict[str, Any]] = None,
    ) -> RationaleCardData:
        """Constructs Rationale Card from an Execution Gap finding."""
        f_id = getattr(finding, "finding_id", uuid.uuid4())
        rule_id = getattr(finding, "rule_id", "EG-UNKNOWN")
        rule_name = getattr(finding, "rule_name", "Execution Gap")
        rule_cat = getattr(finding, "rule_category", "COMPLIANCE_GAP")
        sev = getattr(finding, "severity", "HIGH")
        sev_score = getattr(finding, "severity_score", 75)
        conf = getattr(finding, "confidence", 0.90)
        desc = getattr(finding, "description", "")
        rationale = getattr(finding, "rationale", "")
        evidence_ids = getattr(finding, "evidence_record_ids", [])
        raw_refs = getattr(finding, "raw_evidence_refs", [])
        raw_indices = getattr(finding, "raw_row_indices", [])
        metric_vals = getattr(finding, "metric_values", {})
        recommendation = getattr(finding, "recommendation", "Review and remediate compliance gap.")

        # Trace raw row indices if events_map is provided
        if events_map and not raw_indices:
            for eid in evidence_ids:
                if str(eid) in events_map:
                    ev = events_map[str(eid)]
                    idx = getattr(ev, "raw_row_index", None)
                    if idx is not None and idx not in raw_indices:
                        raw_indices.append(idx)

        tech_details = {
            "condition_evaluated": f"Execution Gap Rule {rule_id} violated",
            "metric_values": metric_vals,
            "evidence_count": len(evidence_ids),
        }

        return RationaleCardData(
            finding_id=f_id,
            entity_id=entity_id,
            engine_name="EXECUTION_GAP",
            rule_code=rule_id,
            title=rule_name,
            severity=sev,
            severity_score=sev_score,
            confidence=conf,
            summary_narrative=rationale or desc,
            technical_details=tech_details,
            recommendation=recommendation,
            evidence_record_ids=[str(e) for e in evidence_ids],
            raw_evidence_refs=raw_refs,
            raw_row_indices=raw_indices,
            metrics_snapshot=metric_vals,
        )

    @staticmethod
    def build_from_negative_space(
        finding: Any,
        entity_id: uuid.UUID,
        events_map: Optional[Dict[str, Any]] = None,
    ) -> RationaleCardData:
        """Constructs Rationale Card from a Negative Space finding."""
        f_id = getattr(finding, "finding_id", uuid.uuid4())
        check_id = getattr(finding, "check_id", "NS-UNKNOWN")
        check_name = getattr(finding, "check_name", "Negative Space Anomaly")
        sev = getattr(finding, "severity", "HIGH")
        sev_score = getattr(finding, "severity_score", 80)
        conf = getattr(finding, "confidence", 0.90)
        rationale = getattr(finding, "rationale", "")
        exp_vol = getattr(finding, "expected_volume", 0.0)
        obs_vol = getattr(finding, "observed_volume", 0.0)
        drop_pct = getattr(finding, "drop_percentage", 0.0)
        entropy = getattr(finding, "entropy_score", None)
        evidence_ids = getattr(finding, "evidence_record_ids", [])
        recommendation = getattr(finding, "recommendation", "Investigate missing telemetry or activity logs.")

        tech_details = {
            "condition_evaluated": f"Absence check {check_id} anomaly threshold breached",
            "threshold_value": exp_vol,
            "observed_value": obs_vol,
            "drop_percentage": drop_pct,
            "entropy_score": entropy,
        }

        metrics = {
            "expected_volume": exp_vol,
            "observed_volume": obs_vol,
            "drop_percentage": drop_pct,
        }
        if entropy is not None:
            metrics["entropy_score"] = entropy

        return RationaleCardData(
            finding_id=f_id,
            entity_id=entity_id,
            engine_name="NEGATIVE_SPACE",
            rule_code=check_id,
            title=check_name,
            severity=sev,
            severity_score=sev_score,
            confidence=conf,
            summary_narrative=rationale,
            technical_details=tech_details,
            recommendation=recommendation,
            evidence_record_ids=[str(e) for e in evidence_ids],
            metrics_snapshot=metrics,
        )

    @staticmethod
    def to_shared_schema(card: RationaleCardData) -> RationaleCard:
        """Converts RationaleCardData to shared RationaleCard schema."""
        from shared.events.enums import SeverityTier
        try:
            sev_enum = SeverityTier(card.severity)
        except (ValueError, KeyError):
            sev_enum = SeverityTier.HIGH

        return RationaleCard(
            title=card.title,
            category=card.engine_name,
            severity=sev_enum,
            rationale_text=card.summary_narrative,
            evidence_record_ids=card.evidence_record_ids,
            raw_evidence_refs=card.raw_evidence_refs,
            metric_values=card.metrics_snapshot,
            recommended_action=card.recommendation,
        )
