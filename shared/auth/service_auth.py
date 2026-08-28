"""FastAPI Authentication and Authorization dependencies."""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.auth.jwt import decode_access_token
from shared.config import settings
from shared.errors import AuthenticationError, PermissionDeniedError
from shared.schemas.auth import TokenPayload

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> TokenPayload:
    """Extracts and verifies JWT token from Authorization Bearer header."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        return payload
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_supervisor(
    token_payload: TokenPayload = Depends(get_current_user_token),
) -> TokenPayload:
    """Ensures caller has the 'supervisor' role."""
    if token_payload.role != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Supervisor role required",
        )
    return token_payload


async def verify_internal_service_key(
    x_internal_service_key: Optional[str] = Header(None, alias="X-Internal-Service-Key"),
) -> str:
    """Validates secret key for inter-service communication (backend -> workers)."""
    if not x_internal_service_key or x_internal_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing internal service key",
        )
    return x_internal_service_key
