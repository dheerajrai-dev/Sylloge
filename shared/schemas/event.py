"""Event schemas and filters."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType, SeverityTier, StandardEventType


class StandardEventCreate(BaseModel):
    """Payload to create normalized standard event."""
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    standard_event_type: StandardEventType
    event_timestamp: datetime
    asset_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[SeverityTier] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    raw_row_index: int
    raw_ref_id: Optional[str] = None
    normalized_payload: Dict[str, Any] = Field(default_factory=dict)


class StandardEventOut(BaseModel):
    """Response DTO for normalized standard event."""
    model_config = ConfigDict(from_attributes=True)

    event_id: uuid.UUID
    submission_id: uuid.UUID
    entity_id: uuid.UUID
    dataset_type: DatasetType
    standard_event_type: StandardEventType
    event_timestamp: datetime
    asset_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[SeverityTier] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    raw_row_index: int
    raw_ref_id: Optional[str] = None
    normalized_payload: Dict[str, Any]
    created_at: datetime


class EventFilterParams(BaseModel):
    """Filter parameters for querying normalized events."""
    entity_id: Optional[uuid.UUID] = None
    dataset_type: Optional[DatasetType] = None
    standard_event_type: Optional[StandardEventType] = None
    asset_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    severity: Optional[SeverityTier] = None
