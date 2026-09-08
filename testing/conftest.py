"""Pytest configuration and shared test fixtures."""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure repository root and all service directories are in sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

for service_dir in ["data_processing", "analytics_engine", "backend", "audit_service", "shared"]:
    service_path = os.path.join(repo_root, service_dir)
    if os.path.isdir(service_path) and service_path not in sys.path:
        sys.path.insert(0, service_path)

# Set test environment overrides before importing shared
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SYNC_DATABASE_URL"] = "sqlite:///:memory:"

from shared.auth.security import hash_password
from shared.db.base import Base
import shared.models  # Register all models
from shared.models.entity import Entity
from shared.models.mapping import FieldMappingProfile
from shared.models.user import User


# Async SQLite engine for async test fixtures
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

# Sync SQLite engine for sync test fixtures
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
    """Provides a fresh, isolated in-memory SQLite database session for async tests."""
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
    """Provides a fresh, isolated in-memory SQLite database session for sync tests."""
    Base.metadata.create_all(test_sync_engine)
    session = TestSyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(test_sync_engine)


@pytest.fixture
def sample_user(sync_db: Session) -> User:
    """Creates a sample supervisor user in the database."""
    user = User(
        user_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        username="test_supervisor",
        password_hash=hash_password("SuperSecretPass123!"),
        full_name="Lead Cyber Inspector",
        role="supervisor",
        is_active=True,
    )
    sync_db.add(user)
    sync_db.commit()
    sync_db.refresh(user)
    return user


@pytest.fixture
def sample_entity(sync_db: Session) -> Entity:
    """Creates a sample supervised entity in the database."""
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


@pytest.fixture
def sample_mapping_profile(sync_db: Session, sample_entity: Entity) -> FieldMappingProfile:
    """Creates a sample field mapping profile."""
    profile = FieldMappingProfile(
        profile_id=uuid.UUID("d2a1b3c4-0001-4000-8000-000000000001"),
        entity_id=sample_entity.entity_id,
        dataset_type="alert_metadata",
        version=1,
        mapping_rules={
            "alert_id": "raw_ref_id",
            "timestamp": "event_timestamp",
            "severity": "severity",
            "rule_name": "action",
            "source_ip": "source_ip",
            "destination_ip": "destination_ip",
            "asset_id": "asset_id",
            "status": "status",
        },
        transform_rules={"date_format": "ISO8601"},
        is_active=True,
    )
    sync_db.add(profile)
    sync_db.commit()
    sync_db.refresh(profile)
    return profile


@pytest.fixture
def entity_id() -> uuid.UUID:
    """Returns sample entity UUID."""
    return uuid.UUID("c1f7a420-5692-4f3b-8511-9a72df894001")


@pytest.fixture
def sample_now() -> datetime:
    """Returns stable fixed timestamp for reproducible testing."""
    return datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def auth_headers() -> dict:
    """Returns inter-service headers for internal API calls."""
    from shared.config import settings
    return {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}


@pytest.fixture
def supervisor_token_headers() -> dict:
    """Returns valid JWT auth headers for supervisor."""
    from shared.auth.jwt import create_access_token
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        username="supervisor",
        role="supervisor",
    )
    return {"Authorization": f"Bearer {token}"}

