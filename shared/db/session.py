"""Database session and connection management."""

from collections.abc import AsyncGenerator, Generator
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config import settings
from shared.db.base import Base

# Async Engine and Session
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Synchronous Engine and Session (for migrations, worker scripts, or synchronous contexts)
sync_engine = create_engine(
    settings.get_sync_database_url,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI async dependency providing transactional database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Generator[Session, None, None]:
    """Synchronous generator providing transactional database session."""
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def init_db_schema() -> None:
    """Creates tables via Alembic migrations and seeds the database."""
    import os
    import subprocess
    from shared.logging import logger
    
    # Run Alembic migrations
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"], 
            check=True, 
            cwd="/app"
        )
        logger.info("Alembic migrations completed successfully.")
    except Exception as e:
        logger.error(f"Failed to run alembic migrations: {e}")
        # We don't return here so seed script can still try to run, or we can return
        
    if os.path.exists("/app/infrastructure/postgres/init.sql"):
        try:
            with open("/app/infrastructure/postgres/init.sql", "r") as f:
                sql = f.read()
            from sqlalchemy import text
            async with async_engine.begin() as conn:
                for statement in sql.split(';'):
                    stmt = statement.strip()
                    if stmt and not stmt.startswith('--'):
                        await conn.execute(text(stmt))
        except Exception as e:
            logger.error(f"Failed to run init.sql: {e}")


async def drop_db_schema() -> None:
    """Drops all tables defined in Base metadata."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
