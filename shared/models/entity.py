"""Entity model for supervised organizations."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType, TimestampMixin

if TYPE_CHECKING:
    from shared.models.audit import AuditManifest
    from shared.models.correlation import Correlation
    from shared.models.dataset import Dataset
    from shared.models.event import NormalizedEvent
    from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
    from shared.models.mapping import FieldMappingProfile
    from shared.models.quarantine import QuarantinedRow
    from shared.models.risk_score import RiskScore
    from shared.models.submission import RawSubmission


class Entity(Base, TimestampMixin):
    """Supervised regulated entity (e.g. Bank, Telco, Energy Provider)."""

    __tablename__ = "entities"

    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    sector: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    size_tier: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    contact_email: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    entity_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # Relationships
    mapping_profiles: Mapped[List["FieldMappingProfile"]] = relationship(
        "FieldMappingProfile",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    datasets: Mapped[List["Dataset"]] = relationship(
        "Dataset",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    raw_submissions: Mapped[List["RawSubmission"]] = relationship(
        "RawSubmission",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    quarantined_rows: Mapped[List["QuarantinedRow"]] = relationship(
        "QuarantinedRow",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    normalized_events: Mapped[List["NormalizedEvent"]] = relationship(
        "NormalizedEvent",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    execution_gap_findings: Mapped[List["ExecutionGapFinding"]] = relationship(
        "ExecutionGapFinding",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    negative_space_findings: Mapped[List["NegativeSpaceFinding"]] = relationship(
        "NegativeSpaceFinding",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    correlations: Mapped[List["Correlation"]] = relationship(
        "Correlation",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    risk_scores: Mapped[List["RiskScore"]] = relationship(
        "RiskScore",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    audit_manifests: Mapped[List["AuditManifest"]] = relationship(
        "AuditManifest",
        back_populates="entity",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_entities_sector_tier", "sector", "size_tier"),
        Index("idx_entities_code", "entity_code"),
    )
