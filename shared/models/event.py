"""Normalized event model for canonical telemetry."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.correlation import Correlation
    from shared.models.entity import Entity
    from shared.models.submission import RawSubmission


class NormalizedEvent(Base):
    """Normalized standard event record."""

    __tablename__ = "normalized_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    submission_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("raw_submissions.submission_id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    dataset_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    standard_event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    action: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    status: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    severity: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    source_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    destination_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    raw_row_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_ref_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    normalized_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    submission: Mapped["RawSubmission"] = relationship(
        "RawSubmission",
        back_populates="normalized_events",
    )
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="normalized_events",
    )
    correlations_as_primary: Mapped[List["Correlation"]] = relationship(
        "Correlation",
        foreign_keys="Correlation.primary_event_id",
        back_populates="primary_event",
        cascade="all, delete-orphan",
    )
    correlations_as_correlated: Mapped[List["Correlation"]] = relationship(
        "Correlation",
        foreign_keys="Correlation.correlated_event_id",
        back_populates="correlated_event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_events_entity_time", "entity_id", "event_timestamp"),
        Index("idx_events_entity_type_time", "entity_id", "standard_event_type", "event_timestamp"),
        Index("idx_events_asset", "entity_id", "asset_id"),
        Index("idx_events_submission", "submission_id"),
    )
