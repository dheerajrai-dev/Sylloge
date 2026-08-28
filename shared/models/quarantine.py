"""Quarantined row model for defective records."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.entity import Entity
    from shared.models.submission import RawSubmission


class QuarantinedRow(Base):
    """Quarantined row preserving defective data with failure diagnosis."""

    __tablename__ = "quarantined_rows"

    quarantine_id: Mapped[uuid.UUID] = mapped_column(
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
    row_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_content: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
    )
    failure_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    failed_fields: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        server_default="[]",
    )
    quarantined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    submission: Mapped["RawSubmission"] = relationship(
        "RawSubmission",
        back_populates="quarantined_rows",
    )
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="quarantined_rows",
    )

    __table_args__ = (
        Index("idx_quarantine_submission", "submission_id", "row_index"),
        Index("idx_quarantine_entity", "entity_id", "quarantined_at"),
    )
