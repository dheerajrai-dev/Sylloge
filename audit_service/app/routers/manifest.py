"""Audit manifest and Merkle verification API router."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth.service_auth import verify_internal_service_key
from shared.config import settings
from shared.db.session import get_db
from shared.errors import NotFoundError, SATSAError
from shared.models.audit import AuditManifest
from shared.schemas.audit import (
    AuditManifestCreate,
    AuditManifestDocument,
    AuditManifestOut,
    AuditVerificationResult,
)
from shared.storage.minio_client import minio_client
from ..manifest.generator import AuditManifestGenerator
from ..manifest.verifier import AuditManifestVerifier

router = APIRouter(prefix="/api/v1/audit", tags=["Audit & Manifest"])


class VerifyRequest(BaseModel):
    manifest_id: uuid.UUID


@router.post("/manifest", response_model=AuditManifestOut, status_code=status.HTTP_201_CREATED)
async def generate_audit_manifest(
    request: AuditManifestCreate,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_internal_service_key),
):
    """Compiles deterministic SHA-256 Merkle root manifest, uploads to MinIO, and records in DB."""
    try:
        _, db_manifest = await AuditManifestGenerator.generate_manifest_async(
            request=request,
            db=db,
        )
        return db_manifest
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audit manifest: {str(exc)}",
        ) from exc


@router.post("/verify", response_model=AuditVerificationResult)
async def verify_audit_manifest(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_internal_service_key),
):
    """Cryptographically verifies a Merkle audit manifest against current DB state."""
    try:
        result = await AuditManifestVerifier.verify_manifest_async(
            manifest_id=request.manifest_id,
            db=db,
        )
        return result
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify manifest: {str(exc)}",
        ) from exc


@router.get("/manifest/{manifest_id}", response_model=AuditManifestOut)
async def get_manifest_by_id(
    manifest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves metadata of a specific audit manifest."""
    res = await db.execute(
        select(AuditManifest).where(AuditManifest.manifest_id == manifest_id)
    )
    manifest = res.scalar_one_or_none()
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit manifest not found: {manifest_id}",
        )
    return manifest


@router.get("/manifest/{manifest_id}/raw")
async def get_raw_manifest_document(
    manifest_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Downloads raw JSON manifest document from MinIO or constructs from DB."""
    res = await db.execute(
        select(AuditManifest).where(AuditManifest.manifest_id == manifest_id)
    )
    manifest = res.scalar_one_or_none()
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit manifest not found: {manifest_id}",
        )

    # Try downloading from MinIO
    try:
        if minio_client.object_exists(settings.BUCKET_AUDIT_MANIFESTS, manifest.minio_manifest_path):
            return minio_client.download_json(settings.BUCKET_AUDIT_MANIFESTS, manifest.minio_manifest_path)
    except Exception:
        pass

    # Fallback to structured DB representation
    return {
        "manifest_id": str(manifest.manifest_id),
        "entity_id": str(manifest.entity_id),
        "period": {
            "start": manifest.period_start.isoformat(),
            "end": manifest.period_end.isoformat(),
        },
        "root_merkle_sha256": manifest.root_merkle_sha256,
        "component_hashes": manifest.component_hashes,
        "file_count": manifest.file_count,
        "event_count": manifest.event_count,
        "finding_count": manifest.finding_count,
        "generated_at": manifest.generated_at.isoformat(),
    }


@router.get("/manifest/entity/{entity_id}/latest", response_model=AuditManifestOut)
async def get_latest_entity_manifest(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves the latest audit manifest for a specific entity."""
    stmt = (
        select(AuditManifest)
        .where(AuditManifest.entity_id == entity_id)
        .order_by(desc(AuditManifest.generated_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    manifest = res.scalar_one_or_none()
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audit manifests found for entity: {entity_id}",
        )
    return manifest


@router.get("/manifests", response_model=List[AuditManifestOut])
async def list_manifests(
    entity_id: Optional[uuid.UUID] = Query(None),
    manifest_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lists audit manifests with optional filters."""
    stmt = select(AuditManifest)
    if entity_id:
        stmt = stmt.where(AuditManifest.entity_id == entity_id)
    if manifest_type:
        stmt = stmt.where(AuditManifest.manifest_type == manifest_type)

    stmt = stmt.order_by(desc(AuditManifest.generated_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
