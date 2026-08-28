"""Unit tests for Execution Gap Engine and Declarative AST Interpreter."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from analytics_engine.engines.execution_gap.engine import ExecutionGapEngine
from analytics_engine.engines.execution_gap.interpreter import LogicInterpreter
from analytics_engine.engines.execution_gap.models import (
    ConditionOperator,
    JoinRelation,
    LogicalOperator,
    RuleCondition,
    RuleDefinition,
    TemporalJoin,
)
from analytics_engine.engines.execution_gap.registry import ExecutionGapRuleRegistry


def test_interpreter_basic_operators():
    """Tests atomic comparison operators in LogicInterpreter."""
    record = {"severity": "CRITICAL", "count": 15, "notes": "ok", "tags": ["prod", "db"]}

    # EQ / NE
    assert LogicInterpreter._apply_operator("CRITICAL", ConditionOperator.EQ, "CRITICAL") is True
    assert LogicInterpreter._apply_operator("HIGH", ConditionOperator.NE, "LOW") is True
    assert LogicInterpreter._apply_operator("HIGH", ConditionOperator.EQ, "LOW") is False

    # Numeric GT / LT / GTE / LTE
    assert LogicInterpreter._apply_operator(15, ConditionOperator.GT, 10) is True
    assert LogicInterpreter._apply_operator(15, ConditionOperator.LTE, 15) is True
    assert LogicInterpreter._apply_operator(5, ConditionOperator.GT, 10) is False

    # IN / NOT_IN
    assert LogicInterpreter._apply_operator("CRITICAL", ConditionOperator.IN, ["CRITICAL", "HIGH"]) is True
    assert LogicInterpreter._apply_operator("LOW", ConditionOperator.NOT_IN, ["CRITICAL", "HIGH"]) is True

    # String operations: LENGTH_LT, REGEX_MATCH, LOWER_IN
    assert LogicInterpreter._apply_operator("short", ConditionOperator.LENGTH_LT, 10) is True
    assert LogicInterpreter._apply_operator("admin_login_fail", ConditionOperator.REGEX_MATCH, r"admin.*fail") is True
    assert LogicInterpreter._apply_operator("Done", ConditionOperator.LOWER_IN, ["done", "fp", "closed"]) is True


def test_interpreter_logical_trees():
    """Tests nested AND, OR, NOT logical expressions in LogicInterpreter."""
    record = {"severity": "HIGH", "status": "OPEN", "duration_hours": 12}

    cond = RuleCondition(
        logical_op=LogicalOperator.AND,
        conditions=[
            RuleCondition(field="severity", operator=ConditionOperator.IN, value=["CRITICAL", "HIGH"]),
            RuleCondition(field="status", operator=ConditionOperator.EQ, value="OPEN"),
            RuleCondition(field="duration_hours", operator=ConditionOperator.GT, value=4),
        ],
    )
    assert LogicInterpreter.evaluate_condition(cond, record) is True

    # Negative branch
    cond_false = RuleCondition(
        logical_op=LogicalOperator.AND,
        conditions=[
            RuleCondition(field="severity", operator=ConditionOperator.EQ, value="LOW"),
            RuleCondition(field="status", operator=ConditionOperator.EQ, value="OPEN"),
        ],
    )
    assert LogicInterpreter.evaluate_condition(cond_false, record) is False


def test_eg_01_uninvestigated_critical_alerts(entity_id: uuid.UUID, sample_now: datetime):
    """EG-01: Verifies uninvestigated critical alert triggers SLA breach finding."""
    engine = ExecutionGapEngine()

    alert = {
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "raw_ref_id": "ALT-001",
        "alert_name": "Ransomware Behavioral Indicator",
        "severity": "CRITICAL",
        "asset_id": "SRV-DC-01",
        "event_timestamp": sample_now - timedelta(hours=3),
        "raw_row_index": 1,
    }

    # Case 1: No investigation exists -> EG-01 triggers
    findings = engine.run([alert], entity_id, sample_now - timedelta(hours=5), sample_now)
    assert len(findings) == 1
    assert findings[0].rule_id == "EG-01"
    assert findings[0].severity in ("HIGH", "CRITICAL")
    assert "ALT-001" in findings[0].rationale
    assert findings[0].evidence_record_ids == [str(alert["event_id"])]

    # Case 2: Investigation exists within 1 hour -> EG-01 does NOT trigger
    investigation = {
        "event_id": uuid.uuid4(),
        "dataset_type": "investigation_records",
        "standard_event_type": "INVESTIGATION",
        "raw_ref_id": "ALT-001",
        "case_id": "CASE-100",
        "event_timestamp": sample_now - timedelta(hours=2, minutes=30),  # 30m after alert
        "investigation_notes": "Triage verified malicious hash. Host isolated.",
    }
    findings_with_inv = engine.run([alert, investigation], entity_id, sample_now - timedelta(hours=5), sample_now)
    eg01 = [f for f in findings_with_inv if f.rule_id == "EG-01"]
    assert len(eg01) == 0


def test_eg_02_missing_escalation(entity_id: uuid.UUID, sample_now: datetime):
    """EG-02: Verifies P1 Critical case open > 4h without escalation triggers finding."""
    engine = ExecutionGapEngine()

    case = {
        "event_id": uuid.uuid4(),
        "dataset_type": "case_management",
        "standard_event_type": "CASE",
        "raw_ref_id": "CASE-P1-99",
        "priority": "P1_CRITICAL",
        "severity": "CRITICAL",
        "status": "OPEN",
        "event_timestamp": sample_now - timedelta(hours=6),
        "raw_row_index": 5,
    }

    findings = engine.run([case], entity_id, sample_now - timedelta(hours=10), sample_now)
    eg02 = [f for f in findings if f.rule_id == "EG-02"]
    assert len(eg02) == 1
    assert eg02[0].severity == "CRITICAL"
    assert "CASE-P1-99" in eg02[0].rationale


def test_eg_03_stale_open_case(entity_id: uuid.UUID, sample_now: datetime):
    """EG-03: Verifies dormant case > 72h triggers finding."""
    engine = ExecutionGapEngine()

    case = {
        "event_id": uuid.uuid4(),
        "dataset_type": "case_management",
        "standard_event_type": "CASE",
        "raw_ref_id": "CASE-STALE-1",
        "status": "OPEN",
        "event_timestamp": sample_now - timedelta(days=5),
        "raw_row_index": 8,
    }

    findings = engine.run([case], entity_id, sample_now - timedelta(days=7), sample_now)
    eg03 = [f for f in findings if f.rule_id == "EG-03"]
    assert len(eg03) == 1
    assert "CASE-STALE-1" in eg03[0].rationale
    assert eg03[0].metric_values["idle_days"] >= 4.0


def test_eg_04_closure_without_resolution_notes(entity_id: uuid.UUID, sample_now: datetime):
    """EG-04: Verifies closure with 'done' or short notes triggers finding."""
    engine = ExecutionGapEngine()

    case = {
        "event_id": uuid.uuid4(),
        "dataset_type": "case_management",
        "standard_event_type": "CASE",
        "raw_ref_id": "CASE-SHORT-NOTE",
        "status": "CLOSED",
        "notes": "fp",  # Non-diligent note
        "event_timestamp": sample_now - timedelta(hours=1),
        "raw_row_index": 12,
    }

    findings = engine.run([case], entity_id, sample_now - timedelta(hours=2), sample_now)
    eg04 = [f for f in findings if f.rule_id == "EG-04"]
    assert len(eg04) == 1
    assert "CASE-SHORT-NOTE" in eg04[0].rationale


def test_eg_05_unassigned_crown_jewel_asset(entity_id: uuid.UUID, sample_now: datetime):
    """EG-05: Verifies alert on unowned Crown Jewel triggers finding."""
    engine = ExecutionGapEngine()

    alert = {
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "raw_ref_id": "ALT-CJ-01",
        "asset_id": "DB-CORE-PROD",
        "severity": "HIGH",
        "criticality_tier": "CROWN_JEWEL",
        "event_timestamp": sample_now - timedelta(minutes=30),
        "raw_row_index": 20,
    }
    asset = {
        "event_id": uuid.uuid4(),
        "dataset_type": "asset_inventory",
        "standard_event_type": "ASSET",
        "asset_id": "DB-CORE-PROD",
        "hostname": "db-core.internal",
        "criticality_tier": "CROWN_JEWEL",
        "owner": None,  # Missing owner
        "department": None,  # Missing department
    }

    findings = engine.run([alert, asset], entity_id, sample_now - timedelta(hours=1), sample_now)
    eg05 = [f for f in findings if f.rule_id == "EG-05"]
    assert len(eg05) == 1
    assert "DB-CORE-PROD" in eg05[0].rationale


def test_eg_06_escalation_without_incident_declaration(entity_id: uuid.UUID, sample_now: datetime):
    """EG-06: Verifies Tier-3 escalation without incident record within 24h triggers finding."""
    engine = ExecutionGapEngine()

    esc = {
        "event_id": uuid.uuid4(),
        "dataset_type": "escalation_records",
        "standard_event_type": "ESCALATION",
        "raw_ref_id": "ESC-101",
        "case_id": "CASE-CRIT-999",
        "escalated_to": "TIER_3_IR",
        "event_timestamp": sample_now - timedelta(hours=30),
        "raw_row_index": 3,
    }

    findings = engine.run([esc], entity_id, sample_now - timedelta(days=2), sample_now)
    eg06 = [f for f in findings if f.rule_id == "EG-06"]
    assert len(eg06) == 1
    assert "CASE-CRIT-999" in eg06[0].rationale


def test_eg_07_rapid_batch_dismissal(entity_id: uuid.UUID, sample_now: datetime):
    """EG-07: Verifies analyst dismissing 10 cases in 60s triggers rubber-stamping finding."""
    engine = ExecutionGapEngine()

    cases = []
    base_t = sample_now - timedelta(minutes=10)
    for i in range(10):
        cases.append({
            "event_id": uuid.uuid4(),
            "dataset_type": "case_management",
            "standard_event_type": "CASE",
            "raw_ref_id": f"CASE-BATCH-{i}",
            "status": "CLOSED",
            "user_id": "analyst_fast_eddie",
            "closed_at": base_t + timedelta(seconds=i * 5),  # 10 cases in 45s (< 120s)
            "raw_row_index": 100 + i,
        })

    findings = engine.run(cases, entity_id, sample_now - timedelta(hours=1), sample_now)
    eg07 = [f for f in findings if f.rule_id == "EG-07"]
    assert len(eg07) == 1
    assert "analyst_fast_eddie" in eg07[0].rationale
    assert len(eg07[0].evidence_record_ids) == 10


def test_eg_08_off_hours_sla_breach(entity_id: uuid.UUID):
    """EG-08: Verifies off-hours critical alert with >60m delay triggers finding."""
    engine = ExecutionGapEngine()

    # Sunday 22:00 UTC (off-hours)
    sunday_night = datetime(2026, 8, 23, 22, 0, 0, tzinfo=timezone.utc)
    eval_end = datetime(2026, 8, 24, 6, 0, 0, tzinfo=timezone.utc)

    alert = {
        "event_id": uuid.uuid4(),
        "dataset_type": "alert_metadata",
        "standard_event_type": "ALERT",
        "raw_ref_id": "ALT-SUNDAY-NIGHT",
        "severity": "CRITICAL",
        "event_timestamp": sunday_night,
        "raw_row_index": 44,
    }

    # First activity was at 23:45 UTC (105 minutes later > 60m SLA)
    activity = {
        "event_id": uuid.uuid4(),
        "dataset_type": "analyst_activity",
        "standard_event_type": "ACTIVITY",
        "raw_ref_id": "ALT-SUNDAY-NIGHT",
        "event_timestamp": sunday_night + timedelta(minutes=105),
    }

    findings = engine.run([alert, activity], entity_id, sunday_night, eval_end)
    eg08 = [f for f in findings if f.rule_id == "EG-08"]
    assert len(eg08) == 1
    assert eg08[0].metric_values["delay_minutes"] == 105
