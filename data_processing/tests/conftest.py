"""Pytest fixtures for data-processing service tests."""

import sys
import os
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure data-processing directory is in sys.path
dp_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if dp_root not in sys.path:
    sys.path.insert(0, dp_root)

# Also ensure workspace root is in sys.path
workspace_root = os.path.dirname(dp_root)
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from shared.db.base import Base
from shared.db.session import get_db
import shared.models
from shared.models.entity import Entity
from shared.models.submission import RawSubmission
from shared.models.mapping import FieldMappingProfile
from app.main import app


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


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Provides an isolated async SQLite DB session."""
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncClient:
    """Async HTTP test client with database dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def sample_test_entity(db_session: AsyncSession) -> Entity:
    """Creates a sample test entity."""
    entity = Entity(
        entity_id=uuid.UUID("a0000000-0000-0000-0000-000000000001"),
        entity_code="TEST_CORP",
        name="Test Corporation",
        sector="Banking",
        size_tier="Tier-1",
        is_active=True,
    )
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)
    return entity


@pytest_asyncio.fixture(scope="function")
async def sample_test_submission(db_session: AsyncSession, sample_test_entity: Entity) -> RawSubmission:
    """Creates a sample raw submission batch."""
    submission = RawSubmission(
        submission_id=uuid.UUID("b0000000-0000-0000-0000-000000000001"),
        entity_id=sample_test_entity.entity_id,
        dataset_type="alert_metadata",
        file_name="alerts.csv",
        file_size_bytes=1024,
        mime_type="text/csv",
        minio_raw_path="raw-submissions/test/alerts.csv",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ingestion_status="PENDING",
    )
    db_session.add(submission)
    await db_session.commit()
    await db_session.refresh(submission)
    return submission
