"""Direct normalization API endpoint."""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from shared.events.enums import DatasetType
from shared.models.mapping import FieldMappingProfile
from shared.schemas.event import StandardEventCreate
from ..mapping.engine import FieldMappingEngine

router = APIRouter(prefix="/api/v1/process", tags=["Normalization"])


class NormalizeRequest(BaseModel):
    """Payload for on-demand normalization."""
    entity_id: uuid.UUID
    dataset_type: DatasetType
    submission_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    records: List[Dict[str, Any]] = Field(..., min_length=1)
    mapping_rules: Optional[Dict[str, str]] = None
    transform_rules: Optional[Dict[str, Any]] = None


class NormalizedRowResult(BaseModel):
    """Normalized row output."""
    raw_row_index: int
    raw_ref_id: Optional[str] = None
    dataset_type: str
    standard_event_type: str
    event_timestamp: str
    asset_id: Optional[str] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    normalized_payload: Dict[str, Any]


class NormalizeResponse(BaseModel):
    """Response containing normalized records."""
    entity_id: uuid.UUID
    dataset_type: DatasetType
    total_records: int
    normalized_records: List[NormalizedRowResult]


@router.post("/normalize", response_model=NormalizeResponse, status_code=status.HTTP_200_OK)
async def normalize_records(payload: NormalizeRequest) -> NormalizeResponse:
    """Directly normalizes an array of raw telemetry records according to supplied or default mapping."""
    temp_profile = None
    if payload.mapping_rules or payload.transform_rules:
        temp_profile = FieldMappingProfile(
            entity_id=payload.entity_id,
            dataset_type=payload.dataset_type.value,
            version=1,
            mapping_rules=payload.mapping_rules or {},
            transform_rules=payload.transform_rules or {},
        )

    engine = FieldMappingEngine(payload.dataset_type, temp_profile)
    normalized_list: List[NormalizedRowResult] = []

    for idx, rec in enumerate(payload.records, start=1):
        norm = engine.normalize_record(rec, idx)
        normalized_list.append(
            NormalizedRowResult(
                raw_row_index=norm["raw_row_index"],
                raw_ref_id=norm["raw_ref_id"],
                dataset_type=norm["dataset_type"],
                standard_event_type=norm["standard_event_type"],
                event_timestamp=norm["event_timestamp"].isoformat(),
                asset_id=norm["asset_id"],
                user_id=norm["user_id"],
                action=norm["action"],
                status=norm["status"],
                severity=norm["severity"],
                source_ip=norm["source_ip"],
                destination_ip=norm["destination_ip"],
                normalized_payload=norm["normalized_payload"],
            )
        )

    return NormalizeResponse(
        entity_id=payload.entity_id,
        dataset_type=payload.dataset_type,
        total_records=len(normalized_list),
        normalized_records=normalized_list,
    )
