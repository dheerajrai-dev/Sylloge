"""Health check router for data-processing microservice."""

import datetime
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import get_db
from ..config import dp_settings

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check verifying microservice liveness and database connectivity."""
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": dp_settings.SERVICE_NAME,
        "version": dp_settings.SERVICE_VERSION,
        "database": db_status,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
