"""Pytest fixtures for analytics-engine service tests."""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Generator, List, Any
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure paths
engine_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
workspace_root = os.path.dirname(engine_root)
for p in [engine_root, workspace_root]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["INTERNAL_SERVICE_KEY"] = "test_internal_service_key_2026"

from shared.db.base import Base
import shared.models
from shared.models.entity import Entity
from shared.models.event import NormalizedEvent
from shared.config import settings

test_async_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

test_sync_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    future=True,
)

TestSyncSessionLocal = sessionmaker(
    bind=test_sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def async_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def sync_db() -> Generator[Session, None, None]:
    Base.metadata.create_all(test_sync_engine)
    session = TestSyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_sync_engine)


@pytest.fixture
def entity_id() -> uuid.UUID:
    return uuid.UUID("c1f7a420-5692-4f3b-8511-9a72df894001")


@pytest.fixture
def sample_now() -> datetime:
    return datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    return {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}


@pytest.fixture
def sample_entity(sync_db: Session) -> Entity:
    entity = Entity(
        entity_id=uuid.UUID("c1f7a420-5692-4f3b-8511-9a72df894001"),
        entity_code="BANK_ALPHA",
        name="Apex National Bank",
        sector="Banking",
        size_tier="Tier-1",
        contact_email="soc@bankalpha.internal",
        is_active=True,
        entity_metadata={"tier_desc": "SIFI Bank", "soc_tier": "24x7"},
    )
    sync_db.add(entity)
    sync_db.commit()
    sync_db.refresh(entity)
    return entity
