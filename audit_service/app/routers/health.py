"""Health check router for Audit Service."""

from datetime import datetime, timezone
from fastapi import APIRouter

from ..config import audit_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Returns service health status."""
    return {
        "status": "HEALTHY",
        "service": audit_settings.SERVICE_NAME,
        "version": audit_settings.SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
