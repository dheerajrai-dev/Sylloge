"""Peer benchmark model for cohort statistical distributions."""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base, GUID


class PeerBenchmark(Base):
    """Sector + Size Tier cohort statistical benchmark."""

    __tablename__ = "peer_benchmarks"

    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    sector: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    size_tier: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    peer_group_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    mean_val: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    std_dev: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p25: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p50: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p75: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    p90: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    is_low_confidence: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "sector",
            "size_tier",
            "metric_name",
            "period_start",
            "period_end",
            name="uq_benchmark_cohort_metric_period",
        ),
        Index("idx_benchmarks_cohort", "sector", "size_tier", "metric_name"),
    )
