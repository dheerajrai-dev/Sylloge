"""Unit tests for offline JWT authentication, bcrypt hashing, and service auth."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from shared.auth.jwt import create_access_token, decode_access_token
from shared.auth.security import hash_password, verify_password
from shared.auth.service_auth import (
    get_current_supervisor,
    get_current_user_token,
    verify_internal_service_key,
)
from shared.errors import AuthenticationError
from shared.config import settings
from shared.schemas.auth import TokenPayload


def test_password_hashing():
    """Verifies bcrypt password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_create_and_decode():
    """Verifies JWT creation and decoding with claims."""
    user_id = str(uuid.uuid4())
    token = create_access_token(
        subject=user_id,
        username="supervisor_admin",
        role="supervisor",
        extra_claims={"soc_unit": "Central-SOC"},
    )

    payload = decode_access_token(token)
    assert payload.sub == user_id
    assert payload.username == "supervisor_admin"
    assert payload.role == "supervisor"
    assert payload.exp > payload.iat


def test_jwt_expired_token():
    """Verifies expired tokens are rejected."""
    user_id = str(uuid.uuid4())
    expired_token = create_access_token(
        subject=user_id,
        username="supervisor_admin",
        expires_delta=timedelta(seconds=-120),  # expired 2 minutes ago
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(expired_token, leeway=0)


def test_jwt_clock_drift_leeway():
    """Verifies clock drift leeway tolerates small offline host time discrepancies."""
    user_id = str(uuid.uuid4())
    drifted_token = create_access_token(
        subject=user_id,
        username="supervisor_admin",
        expires_delta=timedelta(seconds=-30),  # expired 30 seconds ago
    )

    # With default 60s leeway, this should still decode successfully
    payload = decode_access_token(drifted_token, leeway=60)
    assert payload.username == "supervisor_admin"


def test_jwt_invalid_signature():
    """Verifies tokens signed with incorrect secret key are rejected."""
    token = create_access_token(
        subject="user_123",
        username="fake_user",
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(token, secret_key="wrong_secret_key_12345678901234567890")


@pytest.mark.asyncio
async def test_fastapi_auth_dependencies():
    """Verifies FastAPI auth dependencies and role checks."""
    user_id = str(uuid.uuid4())
    valid_token = create_access_token(
        subject=user_id,
        username="supervisor_lead",
        role="supervisor",
    )

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_token)
    token_payload = await get_current_user_token(credentials)
    assert token_payload.username == "supervisor_lead"

    supervisor_token = await get_current_supervisor(token_payload)
    assert supervisor_token.role == "supervisor"

    # Test non-supervisor role rejection
    non_supervisor_payload = TokenPayload(
        sub=user_id,
        username="regular_viewer",
        role="viewer",
        exp=token_payload.exp,
        iat=token_payload.iat,
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_current_supervisor(non_supervisor_payload)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_internal_service_key_validation():
    """Verifies internal service key validation."""
    valid_key = settings.INTERNAL_SERVICE_KEY
    assert await verify_internal_service_key(valid_key) == valid_key

    with pytest.raises(HTTPException) as exc_info:
        await verify_internal_service_key("invalid_key_attempt")
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        await verify_internal_service_key(None)
    assert exc_info.value.status_code == 403
