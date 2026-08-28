"""Authentication module for SAT-SA."""

from shared.auth.jwt import create_access_token, decode_access_token
from shared.auth.security import hash_password, verify_password
from shared.auth.service_auth import (
    get_current_supervisor,
    get_current_user_token,
    verify_internal_service_key,
)

__all__ = [
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
    "get_current_user_token",
    "get_current_supervisor",
    "verify_internal_service_key",
]
