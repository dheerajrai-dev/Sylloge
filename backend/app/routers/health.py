"""Health check router for Backend API Gateway."""

from datetime import datetime, timezone
from fastapi import APIRouter

from ..config import backend_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Returns service health status."""
    return {
        "status": "HEALTHY",
        "service": backend_settings.SERVICE_NAME,
        "version": backend_settings.SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
