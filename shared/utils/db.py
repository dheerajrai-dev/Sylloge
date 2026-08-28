"""Database utilities and connectivity health checks."""

from typing import Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import async_engine, sync_engine
from shared.logging import logger


async def check_async_db_connection() -> Tuple[bool, str]:
    """Checks async database connection health."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True, "Database connection healthy"
    except Exception as exc:
        logger.error(f"Async DB health check failed: {exc}")
        return False, str(exc)


def check_sync_db_connection() -> Tuple[bool, str]:
    """Checks synchronous database connection health."""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection healthy"
    except Exception as exc:
        logger.error(f"Sync DB health check failed: {exc}")
        return False, str(exc)
