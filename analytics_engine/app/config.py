"""Configuration settings for analytics-engine microservice."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from shared.config import settings as global_settings


class AnalyticsEngineSettings(BaseSettings):
    """Analytics engine service settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SERVICE_NAME: str = "analytics-engine"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8002
    HOST: str = "0.0.0.0"

    # Execution Gap Settings
    DEFAULT_SLA_INVESTIGATION_HOURS: int = 2
    DEFAULT_SLA_ESCALATION_HOURS: int = 4
    DEFAULT_STALE_CASE_HOURS: int = 72
    DEFAULT_OFF_HOURS_SLA_MINUTES: int = 60

    # Negative Space Settings
    EWMA_ALPHA: float = 0.20
    EWMA_CLIFF_K: float = 3.0
    MIN_SAMPLE_SIZE_N: int = 15
    SHANNON_ENTROPY_MIN_BITS: float = 0.50
    CV_SYNTHETIC_HEARTBEAT_THRESHOLD: float = 0.01

    # Correlation Settings
    CORRELATION_BURST_WINDOW_HOURS: int = 24
    CORRELATION_REPEAT_ALERT_THRESHOLD: int = 5
    CORRELATION_REPEAT_HIGH_ALERT_THRESHOLD: int = 3
    TFIDF_COSINE_SIMILARITY_THRESHOLD: float = 0.85
    JACCARD_TOKEN_SIMILARITY_THRESHOLD: float = 0.80

    # Peer Benchmark Settings
    MIN_PEER_GROUP_SIZE: int = 3
    PEER_DAMPENING_LAMBDA: float = 0.50

    # Risk Scoring Weights
    WEIGHT_EXECUTION_GAP: float = 0.45
    WEIGHT_NEGATIVE_SPACE: float = 0.35
    WEIGHT_PEER_DEVIATION: float = 0.20


analytics_settings = AnalyticsEngineSettings()
