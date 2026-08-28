"""Unit tests for Explainability Engine and Rationale Card generation."""

from datetime import datetime, timezone
import uuid
import pytest

from analytics_engine.engines.execution_gap.models import ExecutionGapFindingDraft
from analytics_engine.engines.explainability.card_builder import RationaleCardBuilder
from analytics_engine.engines.explainability.engine import ExplainabilityEngine
from analytics_engine.engines.negative_space.models import NegativeSpaceFindingDraft


def test_rationale_card_builder_execution_gap(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies RationaleCard construction from Execution Gap finding."""
    finding = ExecutionGapFindingDraft(
        finding_id=uuid.uuid4(),
        entity_id=entity_id,
        rule_id="EG-01",
        rule_name="Uninvestigated Alerts",
        rule_category="TRIAGE",
        severity="HIGH",
        severity_score=75,
        confidence=0.95,
        period_start=sample_now,
        period_end=sample_now,
        description="Alert ALT-1 uninvestigated.",
        rationale="Alert ALT-1 on host DB-01 received no investigation within 2-hour SLA window.",
        evidence_record_ids=["00000000-0000-0000-0000-000000000001"],
        raw_evidence_refs=["ALT-1"],
        metric_values={"delay_hours": 3.5},
        recommendation="Assign to triage analyst immediately.",
    )

    card = RationaleCardBuilder.build_from_execution_gap(finding, entity_id)

    assert card.engine_name == "EXECUTION_GAP"
    assert card.rule_code == "EG-01"
    assert card.severity == "HIGH"
    assert card.evidence_record_ids == ["00000000-0000-0000-0000-000000000001"]
    assert card.metrics_snapshot["delay_hours"] == 3.5
    assert card.recommendation == "Assign to triage analyst immediately."

    # Convert to shared schema
    shared_card = RationaleCardBuilder.to_shared_schema(card)
    assert shared_card.title == "Uninvestigated Alerts"
    assert str(shared_card.severity) == "CRITICAL" or str(shared_card.severity.value) == "HIGH"


def test_rationale_card_builder_negative_space(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies RationaleCard construction from Negative Space finding."""
    finding = NegativeSpaceFindingDraft(
        finding_id=uuid.uuid4(),
        entity_id=entity_id,
        check_id="NS-03",
        check_name="Zero Crown Jewel Coverage",
        check_category="ASSET_BLINDNESS",
        severity="CRITICAL",
        severity_score=95,
        confidence=0.98,
        period_start=sample_now,
        period_end=sample_now,
        expected_volume=5.0,
        observed_volume=1.0,
        drop_percentage=80.0,
        rationale="4 out of 5 Crown Jewel assets lack active monitoring.",
        evidence_record_ids=["00000000-0000-0000-0000-000000000005"],
        recommendation="Deploy EDR sensors.",
    )

    card = RationaleCardBuilder.build_from_negative_space(finding, entity_id)

    assert card.engine_name == "NEGATIVE_SPACE"
    assert card.rule_code == "NS-03"
    assert card.severity == "CRITICAL"
    assert card.technical_details["drop_percentage"] == 80.0
    assert card.recommendation == "Deploy EDR sensors."


def test_explainability_engine_full_run(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies ExplainabilityEngine orchestrates card generation for mixed findings."""
    engine = ExplainabilityEngine()

    eg = ExecutionGapFindingDraft(
        finding_id=uuid.uuid4(),
        entity_id=entity_id,
        rule_id="EG-03",
        rule_name="Stale Cases",
        rule_category="SLA",
        severity="MEDIUM",
        severity_score=50,
        confidence=0.85,
        period_start=sample_now,
        period_end=sample_now,
        description="Dormant case",
        rationale="Case dormant for 5 days.",
        evidence_record_ids=["e1"],
    )

    ns = NegativeSpaceFindingDraft(
        finding_id=uuid.uuid4(),
        entity_id=entity_id,
        check_id="NS-02",
        check_name="Missing Weekend Activity",
        check_category="COVERAGE",
        severity="HIGH",
        severity_score=80,
        confidence=0.95,
        period_start=sample_now,
        period_end=sample_now,
        expected_volume=30.0,
        observed_volume=0.0,
        drop_percentage=100.0,
        rationale="Zero weekend activity.",
        evidence_record_ids=["e2"],
    )

    cards = engine.generate_cards(entity_id, [eg], [ns])
    assert len(cards) == 2
    assert {c.engine_name for c in cards} == {"EXECUTION_GAP", "NEGATIVE_SPACE"}
