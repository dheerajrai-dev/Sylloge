"""Field mapping profile management endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from shared.events.enums import DatasetType
from shared.models.mapping import FieldMappingProfile
from shared.schemas.mapping import (
    FieldMappingProfileCreate,
    FieldMappingProfileOut,
    FieldMappingProfileUpdate,
)

router = APIRouter(prefix="/api/v1/process/mapping-profiles", tags=["Mapping Profiles"])


@router.post("", response_model=FieldMappingProfileOut, status_code=status.HTTP_201_CREATED)
async def create_or_update_mapping_profile(
    payload: FieldMappingProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> FieldMappingProfileOut:
    """Registers a new or updated field mapping profile for an entity and dataset type."""
    # Find existing highest version
    stmt = (
        select(FieldMappingProfile)
        .where(
            FieldMappingProfile.entity_id == payload.entity_id,
            FieldMappingProfile.dataset_type == payload.dataset_type.value,
        )
        .order_by(FieldMappingProfile.version.desc())
    )
    res = await db.execute(stmt)
    existing = res.scalars().first()

    next_version = (existing.version + 1) if existing else payload.version

    profile = FieldMappingProfile(
        profile_id=uuid.uuid4(),
        entity_id=payload.entity_id,
        dataset_type=payload.dataset_type.value,
        version=next_version,
        mapping_rules=payload.mapping_rules,
        transform_rules=payload.transform_rules,
        is_active=payload.is_active,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return FieldMappingProfileOut.model_validate(profile)


@router.get("/{entity_id}/{dataset_type}", response_model=FieldMappingProfileOut, status_code=status.HTTP_200_OK)
async def get_active_mapping_profile(
    entity_id: uuid.UUID,
    dataset_type: DatasetType,
    db: AsyncSession = Depends(get_db),
) -> FieldMappingProfileOut:
    """Retrieves active field mapping profile for an entity and dataset type."""
    stmt = (
        select(FieldMappingProfile)
        .where(
            FieldMappingProfile.entity_id == entity_id,
            FieldMappingProfile.dataset_type == dataset_type.value,
            FieldMappingProfile.is_active == True,
        )
        .order_by(FieldMappingProfile.version.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    profile = res.scalars().first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active mapping profile found for entity {entity_id} and dataset {dataset_type.value}",
        )
    return FieldMappingProfileOut.model_validate(profile)
