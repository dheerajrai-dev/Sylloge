"""Default 8 MVP Execution Gap declarative rule definitions."""

from typing import List
from .models import (
    ConditionOperator,
    JoinRelation,
    LogicalOperator,
    RuleCondition,
    RuleDefinition,
    TemporalJoin,
)


def get_default_execution_gap_rules() -> List[RuleDefinition]:
    """Returns the 8 authoritative MVP Execution Gap rules (EG-01 to EG-08)."""
    return [
        # Rule EG-01: Uninvestigated Critical / High Alerts
        RuleDefinition(
            rule_code="EG-01",
            name="Uninvestigated Critical / High Alerts",
            category="TRIAGE_FAILURE",
            target_dataset="alert_metadata",
            filter_condition=RuleCondition(
                field="severity",
                operator=ConditionOperator.IN,
                value=["CRITICAL", "HIGH"],
            ),
            temporal_join=TemporalJoin(
                target_dataset="investigation_records",
                join_key="raw_ref_id",
                join_fallback_key="case_id",
                relation=JoinRelation.NOT_EXISTS,
                max_time_delta_seconds=7200,  # 2-hour SLA window
            ),
            severity_base=70,
            severity_multiplier_field="delay_hours",
            severity_multiplier_weight=5.0,
            max_severity=100,
            confidence=0.95,
            description_template="Critical or High severity alert {alert_id} ({alert_name}) uninvestigated after 2-hour SLA.",
            rationale_template="Alert {alert_id} ({alert_name}) on asset {asset_id} with severity {severity} received no investigation within the 2-hour SLA window.",
            recommendation="Enforce immediate triage desk assignment and investigate unhandled high/critical priority alerts.",
        ),

        # Rule EG-02: Missing Escalation After Severity Threshold
        RuleDefinition(
            rule_code="EG-02",
            name="Missing Escalation After Severity Threshold",
            category="ESCALATION_BYPASS",
            target_dataset="case_management",
            filter_condition=RuleCondition(
                logical_op=LogicalOperator.OR,
                conditions=[
                    RuleCondition(field="severity", operator=ConditionOperator.EQ, value="CRITICAL"),
                    RuleCondition(field="priority", operator=ConditionOperator.IN, value=["P1_CRITICAL", "CRITICAL", "P1"]),
                ],
            ),
            temporal_join=TemporalJoin(
                target_dataset="escalation_records",
                join_key="raw_ref_id",
                join_fallback_key="case_id",
                relation=JoinRelation.NOT_EXISTS,
            ),
            severity_base=85,
            confidence=0.90,
            description_template="P1 Critical Case {case_id} remained unescalated beyond 4-hour SLA.",
            rationale_template="P1 Critical Case {case_id} remained unescalated after 4 hours of active status.",
            recommendation="Trigger automatic escalation pathway to Tier-2/Tier-3 IR when P1 cases exceed 4 hours.",
        ),

        # Rule EG-03: Stale Open Cases
        RuleDefinition(
            rule_code="EG-03",
            name="Stale Open Cases",
            category="SLA_DEFICIT",
            target_dataset="case_management",
            filter_condition=RuleCondition(
                field="status",
                operator=ConditionOperator.IN,
                value=["OPEN", "IN_PROGRESS", "ACTIVE"],
            ),
            severity_base=50,
            severity_multiplier_field="idle_days",
            severity_multiplier_weight=5.0,
            max_severity=100,
            confidence=0.85,
            description_template="Case {case_id} has been dormant for over 72 hours without analyst activity.",
            rationale_template="Case {case_id} has been dormant for {idle_days} days without any analyst audit trail or notes.",
            recommendation="Review stale case backlog and reassign or close dormant tickets with updated audit notes.",
        ),

        # Rule EG-04: Case Closure Without Resolution Notes
        RuleDefinition(
            rule_code="EG-04",
            name="Case Closure Without Resolution Notes",
            category="DILIGENCE_FAILURE",
            target_dataset="case_management",
            filter_condition=RuleCondition(
                field="status",
                operator=ConditionOperator.IN,
                value=["CLOSED", "RESOLVED"],
            ),
            severity_base=75,
            confidence=0.95,
            description_template="Case {case_id} closed without adequate resolution notes.",
            rationale_template="Case {case_id} was closed with non-diligent resolution notes (\"{notes}\").",
            recommendation="Enforce mandatory minimum 20-character technical justification for all case closures.",
        ),

        # Rule EG-05: Unassigned Critical Assets in Alerts
        RuleDefinition(
            rule_code="EG-05",
            name="Unassigned Critical Assets in Alerts",
            category="ASSET_GOVERNANCE",
            target_dataset="alert_metadata",
            filter_condition=RuleCondition(
                field="criticality_tier",
                operator=ConditionOperator.IN,
                value=["CROWN_JEWEL", "CRITICAL", "TIER_1"],
            ),
            severity_base=65,
            confidence=0.90,
            description_template="Alert on Crown Jewel asset {asset_id} lacking CMDB ownership.",
            rationale_template="Crown Jewel asset {hostname} ({asset_id}) triggered critical security alerts but lacks an assigned departmental owner in CMDB.",
            recommendation="Update asset CMDB inventory to assign accountable system owners and escalation contacts.",
        ),

        # Rule EG-06: Escalation Without Incident Record
        RuleDefinition(
            rule_code="EG-06",
            name="Escalation Without Incident Record",
            category="INCIDENT_BYPASS",
            target_dataset="escalation_records",
            filter_condition=RuleCondition(
                field="escalated_to",
                operator=ConditionOperator.IN,
                value=["TIER_3_IR", "MANAGEMENT", "EXTERNAL_CERT", "TIER_3"],
            ),
            temporal_join=TemporalJoin(
                target_dataset="incident_reports",
                join_key="case_id",
                join_fallback_key="raw_ref_id",
                relation=JoinRelation.NOT_EXISTS,
                max_time_delta_seconds=86400,  # 24 hours
            ),
            severity_base=80,
            confidence=0.88,
            description_template="Tier-3 IR escalation for Case {case_id} missing incident declaration report.",
            rationale_template="Tier-3 IR escalation for Case {case_id} was not followed by a formal incident declaration report within 24 hours.",
            recommendation="Formalize high-tier escalations by declaring incident records with root-cause analysis.",
        ),

        # Rule EG-07: Rapid Batch Case Dismissal (Rubber-Stamping)
        RuleDefinition(
            rule_code="EG-07",
            name="Rapid Batch Case Dismissal (Rubber-Stamping)",
            category="QUALITY_COMPROMISE",
            target_dataset="case_management",
            severity_base=90,
            confidence=0.92,
            description_template="Analyst {analyst_id} dismissed {batch_count} cases in {seconds} seconds.",
            rationale_template="Analyst {analyst_id} dismissed {batch_count} cases in {seconds} seconds, indicating systematic rubber-stamping.",
            recommendation="Audit bulk dismissal practices and implement rate limiting on analyst case closures.",
        ),

        # Rule EG-08: Off-Hours Critical Alert SLA Breach
        RuleDefinition(
            rule_code="EG-08",
            name="Off-Hours Critical Alert SLA Breach",
            category="OFF_HOURS_DEFICIT",
            target_dataset="alert_metadata",
            filter_condition=RuleCondition(
                field="severity",
                operator=ConditionOperator.IN,
                value=["CRITICAL", "HIGH"],
            ),
            severity_base=85,
            confidence=0.90,
            description_template="Off-hours critical alert {alert_id} triage delay breached 60-minute SLA.",
            rationale_template="Off-hours critical alert {alert_id} experienced triage delay of {delay_minutes} minutes, breaching the 60-minute off-hours SLA.",
            recommendation="Establish on-call 24x7 escalation rotation to handle off-hours and weekend alerts within SLA.",
        ),
    ]
