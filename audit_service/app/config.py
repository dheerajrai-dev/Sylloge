"""SAT-SA Audit Service Settings."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuditSettings(BaseSettings):
    """Audit service configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AUDIT_",
        extra="ignore",
    )

    HOST: str = "0.0.0.0"
    PORT: int = 8003
    SERVICE_NAME: str = "sat-sa-audit-service"
    SERVICE_VERSION: str = "1.0.0"


audit_settings = AuditSettings()
