"""Correlation model for repeat-asset alerts and NLP note similarities."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.entity import Entity
    from shared.models.event import NormalizedEvent


class Correlation(Base):
    """Multi-event correlation and repeat asset clustering link."""

    __tablename__ = "correlations"

    correlation_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    correlation_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    primary_event_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("normalized_events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    correlated_event_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("normalized_events.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    similarity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    shared_attributes: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="correlations",
    )
    primary_event: Mapped["NormalizedEvent"] = relationship(
        "NormalizedEvent",
        foreign_keys=[primary_event_id],
        back_populates="correlations_as_primary",
    )
    correlated_event: Mapped["NormalizedEvent"] = relationship(
        "NormalizedEvent",
        foreign_keys=[correlated_event_id],
        back_populates="correlations_as_correlated",
    )

    __table_args__ = (
        Index("idx_corr_entity_type", "entity_id", "correlation_type"),
        Index("idx_corr_primary", "primary_event_id"),
        Index("idx_corr_correlated", "correlated_event_id"),
    )
