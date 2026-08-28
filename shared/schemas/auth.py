"""Authentication schemas and DTOs."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Login request payload."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class UserOut(BaseModel):
    """User profile response DTO."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class UserCreate(BaseModel):
    """User creation schema."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=128)
    role: str = Field("supervisor", max_length=32)


class TokenResponse(BaseModel):
    """JWT Bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class TokenPayload(BaseModel):
    """Decoded JWT claims payload."""
    sub: str  # user_id
    username: str
    role: str
    exp: int
    iat: int
    jti: Optional[str] = None
