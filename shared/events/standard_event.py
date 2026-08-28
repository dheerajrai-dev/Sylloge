"""Canonical Standard Event schema for SAT-SA."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType, SeverityTier, StandardEventType


class StandardEvent(BaseModel):
    """Canonical event model for all normalized telemetry in SAT-SA."""

    model_config = ConfigDict(from_attributes=True)

    event_id: UUID = Field(default_factory=uuid4, description="Unique standard event ID")
    submission_id: UUID = Field(..., description="Source raw submission batch ID")
    entity_id: UUID = Field(..., description="Target supervised entity ID")
    dataset_type: DatasetType = Field(..., description="Source dataset classification")
    standard_event_type: StandardEventType = Field(..., description="Canonical standard event category")
    event_timestamp: datetime = Field(..., description="Canonical UTC event timestamp")
    asset_id: Optional[str] = Field(None, description="Normalized asset/host identifier")
    user_id: Optional[str] = Field(None, description="Normalized user/analyst identifier")
    action: Optional[str] = Field(None, description="Action or verb for event")
    status: Optional[str] = Field(None, description="Canonical lifecycle status")
    severity: Optional[SeverityTier] = Field(None, description="Normalized severity")
    source_ip: Optional[str] = Field(None, description="IPv4 or IPv6 source address")
    destination_ip: Optional[str] = Field(None, description="IPv4 or IPv6 destination address")
    raw_row_index: int = Field(..., description="0-based line/row index in original submission")
    raw_ref_id: Optional[str] = Field(None, description="Original source ID (e.g. alert_id, case_id)")
    normalized_payload: Dict[str, Any] = Field(default_factory=dict, description="Typed attributes specific to dataset type")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Insertion timestamp")
