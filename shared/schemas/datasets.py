"""Pydantic schemas for the 8 supported dataset types."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertMetadataSchema(BaseModel):
    """Schema for Alert Metadata telemetry."""
    model_config = ConfigDict(extra="allow")

    alert_id: str
    timestamp: datetime
    rule_name: str
    severity: str
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    asset_id: Optional[str] = None
    status: Optional[str] = "OPEN"
    description: Optional[str] = None


class CaseManagementSchema(BaseModel):
    """Schema for Case Management records."""
    model_config = ConfigDict(extra="allow")

    case_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str
    priority: str
    assigned_analyst: Optional[str] = None
    title: str
    description: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None


class InvestigationRecordSchema(BaseModel):
    """Schema for SOC Analyst Investigation records."""
    model_config = ConfigDict(extra="allow")

    investigation_id: str
    case_id: str
    analyst_id: str
    timestamp: datetime
    investigation_action: str
    notes: str
    findings_summary: Optional[str] = None
    time_spent_minutes: Optional[float] = None


class EscalationRecordSchema(BaseModel):
    """Schema for Escalation records (e.g. L1 -> L2/L3)."""
    model_config = ConfigDict(extra="allow")

    escalation_id: str
    case_id: Optional[str] = None
    alert_id: Optional[str] = None
    escalated_from: str
    escalated_to: str
    timestamp: datetime
    escalation_reason: str
    approval_status: Optional[str] = "APPROVED"
    notes: Optional[str] = None


class AssetInventorySchema(BaseModel):
    """Schema for Asset Inventory telemetry."""
    model_config = ConfigDict(extra="allow")

    asset_id: str
    hostname: str
    ip_address: Optional[str] = None
    asset_type: str
    criticality: str  # TIER_1, TIER_2, TIER_3 or HIGH, MEDIUM, LOW
    os: Optional[str] = None
    department: Optional[str] = None
    owner_email: Optional[str] = None
    is_monitored: bool = True


class IncidentReportSchema(BaseModel):
    """Schema for Declared Security Incident Reports."""
    model_config = ConfigDict(extra="allow")

    incident_id: str
    title: str
    severity: str
    declared_at: datetime
    contained_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    affected_assets: Optional[List[str]] = None
    financial_impact: Optional[float] = None


class CoverageReportSchema(BaseModel):
    """Schema for Sensor/Log Coverage telemetry."""
    model_config = ConfigDict(extra="allow")

    coverage_id: str
    tool_name: str
    source_type: str
    total_assets_monitored: int
    active_sensors: int
    coverage_percentage: float
    reported_at: datetime


class AnalystActivitySchema(BaseModel):
    """Schema for Analyst Activity log telemetry."""
    model_config = ConfigDict(extra="allow")

    activity_id: str
    analyst_id: str
    activity_type: str
    timestamp: datetime
    duration_seconds: Optional[int] = None
    entity_ref_id: Optional[str] = None
    session_id: Optional[str] = None
