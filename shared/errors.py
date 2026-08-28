"""Domain and infrastructure exceptions for SAT-SA."""

from typing import Any, Dict, Optional


class SATSAError(Exception):
    """Base exception for all SAT-SA errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(SATSAError):
    """Raised when a requested resource is not found."""
    pass


class AuthenticationError(SATSAError):
    """Raised when authentication fails."""
    pass


class PermissionDeniedError(SATSAError):
    """Raised when authorization or access check fails."""
    pass


class ValidationError(SATSAError):
    """Raised when validation on input data fails."""
    pass


class StorageError(SATSAError):
    """Raised when storage operations (MinIO/S3/disk) fail."""
    pass


class TamperDetectedError(SATSAError):
    """Raised when Merkle tree or SHA-256 cryptographic verification fails."""
    pass


class InternalServiceError(SATSAError):
    """Raised when inter-service communication or remote worker fails."""
    pass
