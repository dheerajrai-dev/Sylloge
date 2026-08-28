"""SAT-SA Cryptographic Audit Microservice Package."""

import os

_as_dir = os.path.dirname(os.path.abspath(__file__))
_as_app_dir = os.path.join(_as_dir, "app")

__path__ = [_as_app_dir, _as_dir]

from audit_service.config import audit_settings
from audit_service.main import app
from audit_service.manifest.generator import AuditManifestGenerator
from audit_service.manifest.verifier import AuditManifestVerifier

__all__ = [
    "app",
    "audit_settings",
    "AuditManifestGenerator",
    "AuditManifestVerifier",
]
