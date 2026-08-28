"""Offline JSON Web Token (JWT) encoding, decoding, and validation."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from shared.config import settings
from shared.errors import AuthenticationError
from shared.schemas.auth import TokenPayload


def create_access_token(
    subject: str,
    username: str,
    role: str = "supervisor",
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Generates a signed HS256 JWT access token for offline air-gapped authentication."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: Dict[str, Any] = {
        "sub": str(subject),
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)

    token = jwt.encode(
        claims,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


def decode_access_token(
    token: str,
    secret_key: Optional[str] = None,
    algorithm: Optional[str] = None,
    leeway: Optional[int] = None,
) -> TokenPayload:
    """Decodes and cryptographically verifies an access token with air-gap clock drift leeway."""
    key = secret_key or settings.JWT_SECRET_KEY
    alg = algorithm or settings.JWT_ALGORITHM
    drift_leeway = leeway if leeway is not None else settings.JWT_LEEWAY_SECONDS

    try:
        payload_dict = jwt.decode(
            token,
            key,
            algorithms=[alg],
            leeway=drift_leeway,
            options={"require": ["sub", "username", "role", "exp", "iat"]},
        )
        return TokenPayload(**payload_dict)
    except ExpiredSignatureError as exc:
        raise AuthenticationError("JWT token has expired") from exc
    except InvalidTokenError as exc:
        raise AuthenticationError(f"Invalid JWT token: {str(exc)}") from exc
    except Exception as exc:
        raise AuthenticationError(f"Authentication token verification failed: {str(exc)}") from exc
