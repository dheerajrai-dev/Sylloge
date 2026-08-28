"""Field mapping profile schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType


class FieldMappingProfileBase(BaseModel):
    """Base fields for field mapping profile."""
    dataset_type: DatasetType
    version: int = Field(1, ge=1)
    mapping_rules: Dict[str, str] = Field(..., description="Mapping from source column name to StandardEvent field name")
    transform_rules: Dict[str, Any] = Field(default_factory=dict, description="Transform functions (e.g. date format, severity map)")
    is_active: bool = True


class FieldMappingProfileCreate(FieldMappingProfileBase):
    """Payload for creating a mapping profile."""
    entity_id: uuid.UUID


class FieldMappingProfileUpdate(BaseModel):
    """Payload for updating a mapping profile."""
    mapping_rules: Optional[Dict[str, str]] = None
    transform_rules: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FieldMappingProfileOut(FieldMappingProfileBase):
    """Response DTO for field mapping profile."""
    model_config = ConfigDict(from_attributes=True)

    profile_id: uuid.UUID
    entity_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
