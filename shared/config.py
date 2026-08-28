"""Configuration settings for SAT-SA microservices."""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings definition for SAT-SA air-gapped system."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application & Environment
    APP_NAME: str = "Sylloge"
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Database Credentials & Connection
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "satsa_db"

    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    SYNC_DATABASE_URL: Optional[str] = None
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @property
    def get_sync_database_url(self) -> str:
        """Returns synchronous database URL for Alembic or sync engines."""
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        if self.DATABASE_URL.startswith("sqlite+aiosqlite://"):
            return self.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
        return self.DATABASE_URL

    # MinIO Object Storage Credentials & Endpoints
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"

    # Bucket Names
    BUCKET_RAW_SUBMISSIONS: str = "raw-submissions"
    BUCKET_QUARANTINED_DUMPS: str = "quarantined-dumps"
    BUCKET_EVIDENCE_RECORDS: str = "evidence-records"
    BUCKET_AUDIT_MANIFESTS: str = "audit-manifests"
    BUCKET_REPORTS: str = "reports"

    # Authentication & Security Keys
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_LEEWAY_SECONDS: int = 60
    INTERNAL_SERVICE_KEY: str = ""
    ADMIN_EMAIL: str = "admin@sylloge.internal"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = ""

    # Service Hosts & Ports
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    DATA_PROCESSING_HOST: str = "0.0.0.0"
    DATA_PROCESSING_PORT: int = 8001
    ANALYTICS_ENGINE_HOST: str = "0.0.0.0"
    ANALYTICS_ENGINE_PORT: int = 8002
    AUDIT_SERVICE_HOST: str = "0.0.0.0"
    AUDIT_SERVICE_PORT: int = 8003

    # Service Interconnect URLs
    BACKEND_API_URL: str = "http://backend:8000"
    DATA_PROCESSING_URL: str = "http://data-processing:8001"
    ANALYTICS_ENGINE_URL: str = "http://analytics-engine:8002"
    AUDIT_SERVICE_URL: str = "http://audit-service:8003"
    FRONTEND_URL: str = "http://frontend:3000"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://frontend:3000",
    ]


settings = Settings()
