"""Dataset catalog schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from shared.events.enums import DatasetType


class DatasetBase(BaseModel):
    """Base fields for dataset catalog item."""
    dataset_type: DatasetType
    display_name: str = Field(..., max_length=128)
    description: Optional[str] = None
    schema_version: str = Field("1.0", max_length=16)


class DatasetCreate(DatasetBase):
    """Payload to register a dataset for an entity."""
    entity_id: uuid.UUID


class DatasetOut(DatasetBase):
    """Response DTO for dataset catalog item."""
    model_config = ConfigDict(from_attributes=True)

    dataset_id: uuid.UUID
    entity_id: uuid.UUID
    created_at: datetime
