"""Audit manifest model for cryptographic Merkle root trails."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.entity import Entity
    from shared.models.submission import RawSubmission


class AuditManifest(Base):
    """Immutable SHA-256 Merkle root audit manifest record."""

    __tablename__ = "audit_manifests"

    manifest_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    submission_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("raw_submissions.submission_id", ondelete="SET NULL"),
        nullable=True,
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    manifest_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    root_merkle_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    file_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    finding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    minio_manifest_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    component_hashes: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="audit_manifests",
    )
    submission: Mapped[Optional["RawSubmission"]] = relationship(
        "RawSubmission",
        back_populates="audit_manifests",
    )

    __table_args__ = (
        Index("idx_manifest_root_sha", "root_merkle_sha256"),
        Index("idx_manifest_entity_period", "entity_id", "period_start", "period_end"),
    )
