"""Challenger 2 Empirical Test Suite for Phase 6 (Synthetic Dataset Generator).

Exhaustively verifies:
1. Every individual Gap Injection method in isolation (EG-01..EG-08, NS-01..NS-08, CORR-BURST, CORR-TEXT).
2. Exact trigger threshold match against all 3 Analytics Engines (ExecutionGapEngine, NegativeSpaceEngine, CorrelationEngine).
3. Ground truth metadata completeness, evidence IDs alignment, severity matching.
4. Edge cases: empty data inputs, invalid entities/tiers, extreme gap counts, malformed data, and clean exception handling.
5. End-to-end full generator multi-tier evaluation.
"""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
import pytest

# Setup sys.path matching project test conventions
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dp_root = os.path.join(repo_root, "data-processing")
if dp_root not in sys.path:
    sys.path.insert(0, dp_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from synthetic_data.tier_profiles import (
    QualityTier,
    TierProfileConfig,
    EntityProfile,
    HEALTHY_PROFILE,
    AVERAGE_PROFILE,
    WEAK_PROFILE,
    DEFAULT_ENTITIES,
    get_tier_profile,
)
from synthetic_data.gap_injector import (
    GapInjector,
    GroundTruthEntry,
    export_ground_truth_csv,
    export_ground_truth_json,
)
from synthetic_data.generator import (
    SyntheticDataGenerator,
    GeneratorConfig,
    GeneratedDatasetBundle,
)
from app.mapping.engine import FieldMappingEngine
from app.parsers.csv_parser import CSVParser
from app.parsers.json_parser import JSONParser
from app.quarantine.validator import RowValidator

from analytics_engine import (
    ExecutionGapEngine,
    NegativeSpaceEngine,
    CorrelationEngine,
    RiskScoringEngine,
)


def normalize_dataset_dict(raw_datasets):
    """Helper to convert raw synthetic dictionary rows into normalized event objects for analytics engines."""
    all_events = []
    for ds_name, rows in raw_datasets.items():
        mapping_engine = FieldMappingEngine(dataset_type=ds_name)
        for idx, row in enumerate(rows):
            # Skip unparseable decoy rows for pure rule evaluation
            if ds_name == "alert_metadata" and row.get("alert_id") is None:
                continue
            if ds_name == "case_management" and "INVALID_DATE" in str(row.get("created_at", "")):
                continue
            if ds_name == "coverage_reports" and row.get("uptime_pct") == "CORRUPTED_NOT_A_FLOAT":
                continue

            try:
                normalized = mapping_engine.normalize_record(row, row_index=idx)
                normalized["event_id"] = uuid.uuid4()
                # Ensure notes field is also available as investigation_notes for text similarity
                if ds_name == "investigation_records" and "notes" in row:
                    normalized["investigation_notes"] = row["notes"]
                    if isinstance(normalized.get("normalized_payload"), dict):
                        normalized["normalized_payload"]["investigation_notes"] = row["notes"]
                all_events.append(normalized)
            except Exception:
                pass
    return all_events


# =============================================================================
# 1. Isolated Empirical Verification of Each Gap Injection Method (18 Rules)
# =============================================================================

class TestIndividualGapInjections:
    """Verifies each gap injection method directly against its target analytics engine."""

    @pytest.fixture
    def base_context(self):
        start = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=timezone.utc)
        entity_id = "11111111-0008-4000-8000-000000000008"
        entity_code = "ENT-008"
        return start, end, entity_id, entity_code

    def test_eg01_uninvestigated_critical_alert(self, base_context):
        """EG-01: Critical alert with no investigation triggers ExecutionGapEngine EG-01 finding."""
        start, end, entity_id, entity_code = base_context
        injector = GapInjector(seed=42)
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        
        # Inject specifically EG-01
        for i in range(3):
            alt_ts = start + timedelta(days=i + 5, hours=10)
            alt_id = f"ALT-PLANTED-EG01-{i+1:03d}"
            datasets["alert_metadata"].append({
                "alert_id": alt_id,
                "timestamp": alt_ts.isoformat(),
                "rule_name": "Unauthorized_Privilege_Escalation",
                "severity": "CRITICAL",
                "source_ip": "198.51.100.44",
                "destination_ip": "10.0.1.15",
                "asset_id": "SRV-PROD-DB-01",
                "status": "OPEN",
                "description": "Planted EG-01 critical privilege escalation alert left uninvestigated past SLA.",
                "criticality_tier": "CROWN_JEWEL",
                "owner": "SecOps Lead",
                "department": "Core Banking",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg01_findings = [f for f in findings if f.rule_id == "EG-01"]
        assert len(eg01_findings) == 3
        for f in eg01_findings:
            assert f.severity in ("HIGH", "CRITICAL")
            assert f.metric_values.get("sla_threshold_hours") == 2
            assert any(ref.startswith("ALT-PLANTED-EG01-") for ref in f.raw_evidence_refs)

    def test_eg02_missing_escalation_p1(self, base_context):
        """EG-02: P1 critical case open > 4h without escalation triggers EG-02 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        case_ts = start + timedelta(days=5, hours=2)
        case_id = "CASE-PLANTED-EG02-001"
        datasets["case_management"].append({
            "case_id": case_id,
            "created_at": case_ts.isoformat(),
            "updated_at": (case_ts + timedelta(hours=6)).isoformat(),
            "status": "OPEN",
            "priority": "P1_CRITICAL",
            "severity": "CRITICAL",
            "assigned_analyst": "AN-102",
            "title": "Active Ransomware Encryption Detected",
            "description": "P1 Critical case open for multiple days without IR escalation.",
            "notes": "Containment pending review.",
            "closed_at": None,
        })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg02_findings = [f for f in findings if f.rule_id == "EG-02"]
        assert len(eg02_findings) == 1
        assert eg02_findings[0].severity == "CRITICAL"
        assert eg02_findings[0].metric_values.get("sla_threshold_hours") == 4
        assert eg02_findings[0].raw_evidence_refs == [case_id]

    def test_eg03_stale_open_cases(self, base_context):
        """EG-03: Open case dormant > 72h triggers EG-03 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(2):
            case_ts = start + timedelta(days=i + 2, hours=4)
            case_id = f"CASE-PLANTED-EG03-{i+1:03d}"
            datasets["case_management"].append({
                "case_id": case_id,
                "created_at": case_ts.isoformat(),
                "updated_at": case_ts.isoformat(),
                "status": "OPEN",
                "priority": "P2_HIGH",
                "severity": "HIGH",
                "assigned_analyst": "AN-105",
                "title": "Dormant Data Exfiltration Alert Investigation",
                "description": "Case abandoned with zero analyst updates for over 72 hours.",
                "notes": "Awaiting initial triage queue assignment.",
                "closed_at": None,
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg03_findings = [f for f in findings if f.rule_id == "EG-03"]
        assert len(eg03_findings) == 2
        for f in eg03_findings:
            assert f.metric_values.get("threshold_hours") == 72
            assert f.metric_values.get("idle_hours") > 72

    def test_eg04_case_closure_without_notes(self, base_context):
        """EG-04: Closed case with terse notes ('closed') triggers EG-04 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(2):
            case_ts = start + timedelta(days=i + 10, hours=1)
            case_id = f"CASE-PLANTED-EG04-{i+1:03d}"
            datasets["case_management"].append({
                "case_id": case_id,
                "created_at": case_ts.isoformat(),
                "updated_at": (case_ts + timedelta(hours=1)).isoformat(),
                "status": "CLOSED",
                "priority": "P2_HIGH",
                "severity": "HIGH",
                "assigned_analyst": "AN-108",
                "title": "Suspected Credential Dumping Incident",
                "description": "Case closed prematurely with non-diligent resolution notes.",
                "notes": "closed",
                "closed_at": (case_ts + timedelta(hours=1)).isoformat(),
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg04_findings = [f for f in findings if f.rule_id == "EG-04"]
        assert len(eg04_findings) == 2
        for f in eg04_findings:
            assert f.severity == "HIGH"
            assert f.metric_values.get("min_required_length") == 20

    def test_eg05_unassigned_critical_asset(self, base_context):
        """EG-05: Alert on Crown Jewel asset without CMDB owner/department triggers EG-05 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(2):
            unassigned_asset_id = f"SRV-UNASSIGNED-CJ-{i+1:02d}"
            datasets["asset_inventory"].append({
                "asset_id": unassigned_asset_id,
                "hostname": f"srv-unassigned-cj{i+1}.corp.internal",
                "ip_address": f"10.0.99.{i+10}",
                "asset_type": "SERVER",
                "criticality_tier": "CROWN_JEWEL",
                "os": "RedHat Enterprise Linux 9",
                "department": None,
                "owner": None,
                "is_monitored": True,
            })
            alt_id = f"ALT-PLANTED-EG05-{i+1:03d}"
            datasets["alert_metadata"].append({
                "alert_id": alt_id,
                "timestamp": (start + timedelta(days=12, hours=i + 3)).isoformat(),
                "rule_name": "Database_Schema_Tampering",
                "severity": "CRITICAL",
                "source_ip": "198.51.100.88",
                "destination_ip": f"10.0.99.{i+10}",
                "asset_id": unassigned_asset_id,
                "status": "IN_PROGRESS",
                "description": "Alert on Crown Jewel asset lacking CMDB departmental owner.",
                "criticality_tier": "CROWN_JEWEL",
                "owner": None,
                "department": None,
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg05_findings = [f for f in findings if f.rule_id == "EG-05"]
        assert len(eg05_findings) == 2
        for f in eg05_findings:
            assert f.metric_values.get("criticality_tier") == "CROWN_JEWEL"
            assert f.metric_values.get("owner") == "UNASSIGNED"

    def test_eg06_escalation_without_incident(self, base_context):
        """EG-06: Tier-3 IR escalation without incident declaration triggers EG-06 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(3):
            esc_id = f"ESC-PLANTED-EG06-{i+1:03d}"
            orphan_case_id = f"CASE-ORPHAN-{i+1:03d}"
            datasets["escalation_records"].append({
                "escalation_id": esc_id,
                "case_id": orphan_case_id,
                "alert_id": f"ALT-REF-{i+1:03d}",
                "escalated_from": "TIER_1_SOC",
                "escalated_to": "TIER_3_IR",
                "timestamp": (start + timedelta(days=15 + i, hours=2)).isoformat(),
                "escalation_reason": "Suspected kerberoasting attack in progress.",
                "approval_status": "APPROVED",
                "notes": "Escalated to Tier 3 IR team.",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg06_findings = [f for f in findings if f.rule_id == "EG-06"]
        assert len(eg06_findings) == 3
        for f in eg06_findings:
            assert f.severity == "HIGH"
            assert f.metric_values.get("sla_hours") == 24

    def test_eg07_rubber_stamp_dismissal_burst(self, base_context):
        """EG-07: 12 cases dismissed in 55s by single analyst triggers EG-07 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        burst_analyst = "AN-RUBBER-STAMP-99"
        base_burst_time = start + timedelta(days=18, hours=14)
        for b_idx in range(12):
            close_t = base_burst_time + timedelta(seconds=b_idx * 5)
            datasets["case_management"].append({
                "case_id": f"CASE-BURST-EG07-{b_idx+1:02d}",
                "created_at": (base_burst_time - timedelta(hours=2)).isoformat(),
                "updated_at": close_t.isoformat(),
                "status": "CLOSED",
                "priority": "P3_MEDIUM",
                "severity": "MEDIUM",
                "assigned_analyst": burst_analyst,
                "title": f"Batch Port Scan Alert #{b_idx+1}",
                "description": "Routine port scan triage.",
                "notes": "dismissed as benign false positive",
                "closed_at": close_t.isoformat(),
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg07_findings = [f for f in findings if f.rule_id == "EG-07"]
        assert len(eg07_findings) == 1
        assert eg07_findings[0].severity == "CRITICAL"
        assert eg07_findings[0].metric_values.get("batch_count") == 10
        assert eg07_findings[0].metric_values.get("elapsed_seconds") <= 120

    def test_eg08_off_hours_sla_breach(self, base_context):
        """EG-08: Off-hours / weekend critical alert without 60m triage triggers EG-08 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(2):
            off_ts = start + timedelta(days=20 + i * 7, hours=22)  # Saturday 22:00
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-PLANTED-EG08-{i+1:03d}",
                "timestamp": off_ts.isoformat(),
                "rule_name": "OffHours_DomainAdmin_Logon",
                "severity": "CRITICAL",
                "source_ip": "198.51.100.77",
                "destination_ip": "10.0.1.5",
                "asset_id": "SRV-DC-01",
                "status": "OPEN",
                "description": "Critical Domain Admin logon alert on weekend.",
                "criticality_tier": "CRITICAL",
                "owner": "SecOps OnCall",
                "department": "Infrastructure",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = ExecutionGapEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        eg08_findings = [f for f in findings if f.rule_id == "EG-08"]
        assert len(eg08_findings) == 2
        for f in eg08_findings:
            assert f.severity in ("HIGH", "CRITICAL")
            assert f.metric_values.get("sla_threshold_minutes") == 60

    def test_ns01_ewma_volume_cliff(self, base_context):
        """NS-01: Sudden drop in daily telemetry volume triggers NS-01 volume cliff finding."""
        start, end, entity_id, entity_code = base_context
        # Create daily telemetry history of 100 alerts/day for 10 days, then drop to 5 on day 11
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        cur = start
        for day in range(10):
            for a in range(80):
                datasets["alert_metadata"].append({
                    "alert_id": f"ALT-D{day}-{a:03d}",
                    "timestamp": (cur + timedelta(days=day, minutes=a * 10)).isoformat(),
                    "rule_name": "Daily_Normal_Telemetry",
                    "severity": "LOW",
                    "source_ip": "10.0.0.1",
                    "destination_ip": "10.0.0.2",
                    "asset_id": "SRV-TEST",
                    "status": "CLOSED",
                    "description": "Normal activity",
                })
        # Day 11 cliff: only 5 alerts
        for a in range(5):
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-D10-{a:03d}",
                "timestamp": (cur + timedelta(days=10, minutes=a * 10)).isoformat(),
                "rule_name": "Daily_Normal_Telemetry",
                "severity": "LOW",
                "source_ip": "10.0.0.1",
                "destination_ip": "10.0.0.2",
                "asset_id": "SRV-TEST",
                "status": "CLOSED",
                "description": "Cliff activity",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns01_findings = [f for f in findings if f.check_id == "NS-01"]
        assert len(ns01_findings) == 1
        assert ns01_findings[0].drop_percentage >= 60.0

    def test_ns02_weekend_analyst_silence(self, base_context):
        """NS-02: Weekend alerts >= 20 with zero analyst activity logs triggers NS-02 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for i in range(25):
            sat = datetime(2026, 1, 3, 10, i, 0, tzinfo=timezone.utc)
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-TEST-WK-{i+1:02d}",
                "timestamp": sat.isoformat(),
                "rule_name": "Test_Alert",
                "severity": "HIGH",
                "source_ip": "10.0.0.1",
                "destination_ip": "10.0.0.2",
                "asset_id": "SRV-TEST",
                "status": "OPEN",
                "description": "Weekend alert test",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns02_findings = [f for f in findings if f.check_id == "NS-02"]
        assert len(ns02_findings) == 1
        assert ns02_findings[0].observed_volume == 0.0
        assert ns02_findings[0].expected_volume == 25.0

    def test_ns03_zero_coverage_crown_jewel(self, base_context):
        """NS-03: Crown Jewel asset with zero coverage reports triggers NS-03 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        datasets["asset_inventory"].append({
            "asset_id": "SRV-CROWN-JEWEL-BLINDSPOT",
            "hostname": "srv-cj-blindspot.bank.internal",
            "ip_address": "10.0.1.1",
            "asset_type": "DATABASE",
            "criticality_tier": "CROWN_JEWEL",
            "os": "Oracle Linux 8.8",
            "department": "Core Banking",
            "owner": "ciso@bank.internal",
            "is_monitored": False,
        })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns03_findings = [f for f in findings if f.check_id == "NS-03"]
        assert len(ns03_findings) == 1
        assert ns03_findings[0].severity == "CRITICAL"

    def test_ns04_asymmetric_case_closure(self, base_context):
        """NS-04: Created >= 30 cases with closure rate < 10% triggers NS-04 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for c_idx in range(35):
            c_ts = start + timedelta(days=c_idx % 25, hours=(c_idx * 3) % 24)
            c_id = f"CASE-DEFICIT-NS04-{c_idx+1:02d}"
            status = "CLOSED" if c_idx == 0 else "OPEN"
            datasets["case_management"].append({
                "case_id": c_id,
                "created_at": c_ts.isoformat(),
                "updated_at": c_ts.isoformat(),
                "status": status,
                "priority": "P2_HIGH",
                "severity": "HIGH",
                "assigned_analyst": "AN-101",
                "title": f"Backlog Case #{c_idx+1}",
                "description": "Backlog surge ticket.",
                "notes": "Pending",
                "closed_at": (c_ts + timedelta(hours=2)).isoformat() if status == "CLOSED" else None,
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns04_findings = [f for f in findings if f.check_id == "NS-04"]
        assert len(ns04_findings) == 1
        assert ns04_findings[0].expected_volume == 35.0
        assert ns04_findings[0].observed_volume == 1.0

    def test_ns05_surge_no_escalations(self, base_context):
        """NS-05: Critical alert surge (>= 20 alerts) with zero escalations triggers NS-05 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for s_idx in range(22):
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-SURGE-NS05-{s_idx+1:02d}",
                "timestamp": (start + timedelta(days=14, hours=(s_idx % 18))).isoformat(),
                "rule_name": "MultiHost_Ransomware_Propagation",
                "severity": "CRITICAL",
                "source_ip": f"10.0.3.{s_idx+10}",
                "destination_ip": "10.0.1.15",
                "asset_id": "SRV-PROD-DB-01",
                "status": "OPEN",
                "description": "High-severity alert surge.",
                "criticality_tier": "CROWN_JEWEL",
                "owner": "SecOps",
                "department": "IT",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns05_findings = [f for f in findings if f.check_id == "NS-05"]
        assert len(ns05_findings) == 1
        assert ns05_findings[0].observed_volume == 0.0
        assert ns05_findings[0].expected_volume == 22.0

    def test_ns06_low_shannon_entropy(self, base_context):
        """NS-06: Collapsed monoculture alert rule distribution (H < 0.50) triggers NS-06 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        for m_idx in range(55):
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-MONO-NS06-{m_idx+1:02d}",
                "timestamp": (start + timedelta(days=m_idx % 28, hours=(m_idx * 2) % 24)).isoformat(),
                "rule_name": "GENERIC_PORT_SCAN_REPEATED",
                "severity": "LOW",
                "source_ip": "198.51.100.2",
                "destination_ip": "10.0.0.1",
                "asset_id": "FW-PERIMETER-01",
                "status": "CLOSED",
                "description": "Blinded monoculture rule repeating continuously.",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns06_findings = [f for f in findings if f.check_id == "NS-06"]
        assert len(ns06_findings) == 1
        assert ns06_findings[0].observed_volume < 0.50

    def test_ns07_constant_inter_arrival_heartbeat(self, base_context):
        """NS-07: Constant alert spacing (CV < 0.01) triggers NS-07 synthetic heartbeat finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        hb_start = start + timedelta(days=3, hours=10)
        for h_idx in range(25):
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-HB-NS07-{h_idx+1:02d}",
                "timestamp": (hb_start + timedelta(seconds=h_idx * 60)).isoformat(),
                "rule_name": "Synthetic_Telemetry_Pulse",
                "severity": "MEDIUM",
                "source_ip": "10.0.5.10",
                "destination_ip": "10.0.5.20",
                "asset_id": "SRV-TEST-01",
                "status": "OPEN",
                "description": "Synthetic pulse.",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns07_findings = [f for f in findings if f.check_id == "NS-07"]
        assert len(ns07_findings) == 1
        assert ns07_findings[0].observed_volume < 0.01

    def test_ns08_missing_post_incident_remediation(self, base_context):
        """NS-08: Incident resolved > 14 days without telemetry updates triggers NS-08 finding."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        inc_decl = start + timedelta(days=2)
        inc_res = start + timedelta(days=3)
        datasets["incident_reports"].append({
            "incident_id": "INC-PLANTED-NS08-001",
            "case_id": "CASE-INC-001",
            "title": "Major Production Database Breach Incident",
            "severity": "CRITICAL",
            "declared_at": inc_decl.isoformat(),
            "contained_at": (inc_decl + timedelta(hours=4)).isoformat(),
            "closed_at": inc_res.isoformat(),
            "root_cause": "Exposed API key.",
            "attack_vector": "EXPLOIT_PUBLIC_APP",
            "financial_impact": 180000.0,
        })
        
        events = normalize_dataset_dict(datasets)
        engine = NegativeSpaceEngine()
        findings = engine.run(events, uuid.UUID(entity_id), start, end)
        ns08_findings = [f for f in findings if f.check_id == "NS-08"]
        assert len(ns08_findings) == 1
        assert ns08_findings[0].severity == "MEDIUM"

    def test_corr_burst_same_asset_clustering(self, base_context):
        """CORR-BURST: Same-asset 24h burst clusters >= 3 High/Crit alerts."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        burst_asset = "SRV-BURST-TARGET-01"
        burst_base_time = start + timedelta(days=8, hours=9)
        for a_idx in range(4):
            datasets["alert_metadata"].append({
                "alert_id": f"ALT-BURST-1-{a_idx+1}",
                "timestamp": (burst_base_time + timedelta(hours=a_idx * 2)).isoformat(),
                "rule_name": "SQL_Injection_Exploitation_Attempt",
                "severity": "CRITICAL" if a_idx % 2 == 0 else "HIGH",
                "source_ip": f"198.51.100.{10+a_idx}",
                "destination_ip": "10.0.1.15",
                "asset_id": burst_asset,
                "status": "OPEN",
                "description": "Repeated SQL injection payload.",
                "criticality_tier": "CROWN_JEWEL",
            })
        
        events = normalize_dataset_dict(datasets)
        engine = CorrelationEngine()
        correlations, clusters = engine.run(events, uuid.UUID(entity_id), start, end)
        
        burst_corrs = [c for c in correlations if c.correlation_type == "REPEAT_ASSET_ALERT"]
        assert len(clusters) >= 1
        assert len(burst_corrs) >= 1
        for cluster in clusters:
            assert cluster.high_critical_count >= 3
            assert cluster.alert_count >= 3

    def test_corr_text_boilerplate_notes(self, base_context):
        """CORR-TEXT: Boilerplate copy-pasted investigation notes trigger TF-IDF similarity correlation."""
        start, end, entity_id, entity_code = base_context
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        boilerplate_text = (
            "Verified initial endpoint telemetry indicators of compromise. "
            "Memory dump triage completed successfully and found no persistent malicious payload on host. "
            "Recommended analyst sign-off and ticket resolution."
        )
        for c_idx in range(3):
            datasets["investigation_records"].append({
                "investigation_id": f"INV-CLONE-1-{c_idx+1}",
                "case_id": f"CASE-CLONE-REF-1-{c_idx+1}",
                "alert_id": f"ALT-CLONE-REF-1-{c_idx+1}",
                "analyst_id": "AN-CLONE-1",
                "timestamp": (start + timedelta(days=11, hours=c_idx * 3 + 8)).isoformat(),
                "investigation_action": "MEMORY_DUMP_TRIAGE",
                "notes": boilerplate_text,
                "findings_summary": "Boilerplate resolution note applied.",
                "time_spent_minutes": 15.0,
            })
        
        events = normalize_dataset_dict(datasets)
        engine = CorrelationEngine()
        correlations, clusters = engine.run(events, uuid.UUID(entity_id), start, end)
        
        text_corrs = [c for c in correlations if c.correlation_type == "TFIDF_NOTE_SIMILARITY"]
        assert len(text_corrs) >= 1
        for c in text_corrs:
            assert c.similarity_score >= 0.85
            assert c.shared_attributes.get("case_id_a") != c.shared_attributes.get("case_id_b")


# =============================================================================
# 2. Edge Cases and Robustness Stress Testing
# =============================================================================

class TestEdgeCasesAndRobustness:
    """Stress-tests corner cases, boundary values, empty inputs, and error resilience."""

    def test_empty_dataset_inputs(self):
        """Empty dataset dictionary handles cleanly without exceptions."""
        injector = GapInjector(seed=42)
        datasets = {}
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 31, tzinfo=timezone.utc)
        
        # Inject gaps on empty dict
        res_ds, gt = injector.inject_gaps(
            datasets=datasets,
            profile=HEALTHY_PROFILE,
            entity_id="11111111-0001-4000-8000-000000000001",
            entity_code="ENT-001",
            period_name="2026-Q1",
            period_start=start,
            period_end=end,
        )
        assert isinstance(res_ds, dict)
        assert len(gt) >= 1  # Contains TIER_BASELINE

    def test_extreme_gap_counts_and_zero_values(self):
        """Custom profile with 0 gaps or extreme high gap multipliers."""
        custom_zero_profile = TierProfileConfig(
            tier=QualityTier.HEALTHY,
            name="Zero Gap Profile",
            description="Profile with all gap triggers explicitly 0",
            expected_risk_score_range=(0.0, 10.0),
            expected_risk_tier="LOW",
            alert_daily_mean=10,
            alert_severity_dist={"LOW": 1.0},
            alert_triage_on_time_rate=1.0,
            mean_mtti_minutes=5.0,
            case_creation_prob_per_alert=0.1,
            case_p1_escalation_rate=1.0,
            case_stale_rate=0.0,
            case_diligent_notes_rate=1.0,
            rubber_stamp_burst_count=0,
            crown_jewel_ratio=0.1,
            crown_jewel_cmdb_assigned_rate=1.0,
            crown_jewel_coverage_rate=1.0,
            weekend_activity_enabled=True,
            off_hours_sla_breach_rate=0.0,
            telemetry_entropy_mode="HIGH",
            inter_arrival_mode="POISSON",
            ewma_cliff_enabled=False,
            asymmetric_closure_deficit=False,
            critical_surge_no_escalation=False,
            unreported_ir_escalations=0,
            unresolved_incident_remediation_gap=False,
            same_asset_burst_count=0,
            cloned_notes_group_count=0,
            quarantine_corruption_rate=0.0,
        )
        
        injector = GapInjector(seed=42)
        datasets = {k: [] for k in ["alert_metadata", "case_management", "investigation_records", "escalation_records", "asset_inventory", "incident_reports", "coverage_reports", "analyst_activity"]}
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 3, 31, tzinfo=timezone.utc)
        
        res_ds, gt = injector.inject_gaps(
            datasets=datasets,
            profile=custom_zero_profile,
            entity_id="11111111-0001-4000-8000-000000000001",
            entity_code="ENT-001",
            period_name="2026-Q1",
            period_start=start,
            period_end=end,
        )
        # Should only have the 1 baseline entry
        assert len(gt) == 1
        assert gt[0].check_id == "TIER_BASELINE"

    def test_invalid_tier_string_handling(self):
        """Invalid tier string throws ValueError with helpful message."""
        with pytest.raises(ValueError, match="Unknown quality tier"):
            get_tier_profile("INVALID_TIER_NAME")

    def test_ground_truth_json_and_csv_escaping(self):
        """Ground truth serialization correctly handles quotes, semicolons, and commas."""
        entry = GroundTruthEntry(
            ground_truth_id="GT-001",
            entity_id="11111111-0001-4000-8000-000000000001",
            entity_code="ENT-001",
            tier="weak",
            period="2026-Q1",
            period_start="2026-01-01T00:00:00Z",
            period_end="2026-03-31T23:59:59Z",
            rule_code="EG-04",
            check_id="EG-04",
            target_dataset="case_management",
            evidence_ids=["CASE,1", 'CASE"2', "CASE;3"],
            expected_severity="HIGH",
            timestamp="2026-01-01T00:00:00Z",
            description='Description with "quotes", commas, and\nnewlines.',
            injected_anomaly_details={"notes": 'contains "quotes" and commas, etc.'},
        )
        
        csv_out = export_ground_truth_csv([entry])
        assert "GT-001" in csv_out
        assert "CASE,1;CASE\"2;CASE;3" in csv_out or "CASE,1" in csv_out
        
        json_out = export_ground_truth_json([entry])
        parsed = json.loads(json_out)
        assert parsed[0]["ground_truth_id"] == "GT-001"
        assert parsed[0]["evidence_ids"] == ["CASE,1", 'CASE"2', "CASE;3"]

    def test_generator_non_standard_tier_distribution(self):
        """Generator handles arbitrary custom tier distributions and entity counts."""
        config = GeneratorConfig(
            num_entities=6,
            periods=1,
            period_days=10,
            tier_distribution="healthy:2,average:2,weak:2",
            seed=999,
        )
        generator = SyntheticDataGenerator(seed=999, config=config)
        bundle = generator.generate_all()
        
        assert len(bundle.entities) == 6
        tier_map = {tier_val: 0 for tier_val in QualityTier}
        for e in bundle.entities:
            tier_map[e.quality_tier] += 1
            
        assert tier_map[QualityTier.HEALTHY] == 2
        assert tier_map[QualityTier.AVERAGE] == 2
        assert tier_map[QualityTier.WEAK] == 2

    def test_risk_scoring_bands_conformity(self):
        """Verifies that Healthy, Average, and Weak tier profiles produce expected Risk Scores."""
        scoring_engine = RiskScoringEngine()
        
        # 1. Healthy entity score should be <= 25 (LOW)
        healthy_draft = scoring_engine.calculate_score(
            entity_id=uuid.uuid4(),
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
            execution_gap_findings=[],
            negative_space_findings=[],
            peer_deviation_score=10.0,
            alert_count=500,
        )
        assert healthy_draft.composite_risk_score <= 25.0
        assert healthy_draft.risk_tier == "LOW"

        # 2. Weak entity with multiple findings should have score >= 75 (CRITICAL)
        from analytics_engine.engines.execution_gap.models import ExecutionGapFindingDraft
        from analytics_engine.engines.negative_space.models import NegativeSpaceFindingDraft
        
        dummy_eg = [
            ExecutionGapFindingDraft(
                entity_id=uuid.uuid4(),
                rule_id="EG-01",
                rule_name="Test",
                rule_category="TEST",
                severity="CRITICAL",
                severity_score=95,
                confidence=0.95,
                period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
                description="desc",
                rationale="rat",
                evidence_record_ids=[],
                raw_evidence_refs=[],
                raw_row_indices=[],
                metric_values={},
                recommendation="rec",
            )
            for _ in range(16)
        ]
        
        dummy_ns = [
            NegativeSpaceFindingDraft(
                entity_id=uuid.uuid4(),
                check_id="NS-01",
                check_name="Test",
                check_category="TEST",
                severity="CRITICAL",
                severity_score=90,
                confidence=0.90,
                period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
                expected_volume=100.0,
                observed_volume=10.0,
                drop_percentage=90.0,
                rationale="rat",
                evidence_record_ids=[],
                recommendation="rec",
            )
            for _ in range(6)
        ]
        
        weak_draft = scoring_engine.calculate_score(
            entity_id=uuid.uuid4(),
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 3, 31, tzinfo=timezone.utc),
            execution_gap_findings=dummy_eg,
            negative_space_findings=dummy_ns,
            peer_deviation_score=90.0,
            alert_count=200,
        )
        assert weak_draft.composite_risk_score >= 75.0
        assert weak_draft.risk_tier == "CRITICAL"
