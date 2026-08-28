"""Supervised Entity schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shared.events.enums import SectorType, SizeTier


class EntityBase(BaseModel):
    """Base fields for regulated entity."""
    entity_code: str = Field(..., min_length=2, max_length=32, description="Unique alphanumeric identifier")
    name: str = Field(..., min_length=2, max_length=255, description="Full organization name")
    sector: str = Field(..., description="Sector e.g. Banking, Telecom, Energy")
    size_tier: str = Field(..., description="Tier-1, Tier-2, or Tier-3")
    contact_email: Optional[str] = Field(None, max_length=128)
    is_active: bool = True
    entity_metadata: Dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    """Payload for registering a new entity."""
    pass


class EntityUpdate(BaseModel):
    """Payload for updating entity details."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    sector: Optional[str] = None
    size_tier: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None
    entity_metadata: Optional[Dict[str, Any]] = None


class EntityOut(EntityBase):
    """Full entity response DTO."""
    model_config = ConfigDict(from_attributes=True)

    entity_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EntitySummary(BaseModel):
    """Summary of entity status and scores for dashboard worklists."""
    model_config = ConfigDict(from_attributes=True)

    entity_id: uuid.UUID
    entity_code: str
    name: str
    sector: str
    size_tier: str
    is_active: bool
    latest_risk_score: Optional[float] = None
    latest_risk_tier: Optional[str] = None
    latest_trend: Optional[str] = None
    open_findings_count: int = 0
