"""Backend API Gateway Configuration Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.config import settings as global_settings


class BackendSettings(BaseSettings):
    """Configuration for FastAPI Backend API Gateway."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    HOST: str = global_settings.BACKEND_HOST
    PORT: int = global_settings.BACKEND_PORT
    SERVICE_NAME: str = "sat-sa-backend-gateway"
    SERVICE_VERSION: str = "1.0.0"

    # Microservice URLs
    DATA_PROCESSING_URL: str = global_settings.DATA_PROCESSING_URL
    ANALYTICS_ENGINE_URL: str = global_settings.ANALYTICS_ENGINE_URL
    AUDIT_SERVICE_URL: str = global_settings.AUDIT_SERVICE_URL


backend_settings = BackendSettings()
