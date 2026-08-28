"""Raw submission batch model for uploaded files."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID

if TYPE_CHECKING:
    from shared.models.audit import AuditManifest
    from shared.models.entity import Entity
    from shared.models.event import NormalizedEvent
    from shared.models.quarantine import QuarantinedRow


class RawSubmission(Base):
    """Raw uploaded submission batch."""

    __tablename__ = "raw_submissions"

    submission_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
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
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    minio_raw_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    valid_row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    quarantined_row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    ingestion_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
    )
    error_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="raw_submissions",
    )
    quarantined_rows: Mapped[List["QuarantinedRow"]] = relationship(
        "QuarantinedRow",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    normalized_events: Mapped[List["NormalizedEvent"]] = relationship(
        "NormalizedEvent",
        back_populates="submission",
        cascade="all, delete-orphan",
    )
    audit_manifests: Mapped[List["AuditManifest"]] = relationship(
        "AuditManifest",
        back_populates="submission",
    )

    __table_args__ = (
        Index("idx_submissions_entity_type", "entity_id", "dataset_type"),
        Index("idx_submissions_sha256", "sha256_hash"),
        Index("idx_submissions_status", "ingestion_status"),
    )
