"""Configuration settings for data-processing microservice."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.config import settings as global_settings


class DataProcessingSettings(BaseSettings):
    """Data processing service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "data-processing"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8001
    HOST: str = "0.0.0.0"
    
    # Ingestion batch processing configuration
    BATCH_INSERT_SIZE: int = 1000
    MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100MB
    DEFAULT_TIMEZONE: str = "UTC"
    
    # Quarantine configuration
    AUTO_QUARANTINE_ON_VALIDATION_ERROR: bool = True
    MAX_ERRORS_PER_ROW: int = 10


dp_settings = DataProcessingSettings()
