"""Healthcheck endpoints for analytics-engine microservice."""

from fastapi import APIRouter
from ..config import analytics_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Returns microservice health and operational status."""
    return {
        "status": "ok",
        "service": analytics_settings.SERVICE_NAME,
        "version": analytics_settings.SERVICE_VERSION,
    }
