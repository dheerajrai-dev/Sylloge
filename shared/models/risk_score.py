"""Risk score model for composite supervisory scores."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.entity import Entity


class RiskScore(Base):
    """Composite 0-100 supervisory risk score with component breakdowns."""

    __tablename__ = "risk_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
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
    composite_risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    execution_gap_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    negative_space_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    peer_deviation_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    weights_applied: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )
    risk_tier: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    trend_direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    rationale_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="risk_scores",
    )

    __table_args__ = (
        Index("idx_risk_entity_period", "entity_id", "period_start", "period_end"),
        Index("idx_risk_composite", "composite_risk_score"),
    )
