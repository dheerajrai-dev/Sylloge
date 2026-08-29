"""Execution gap and negative space finding models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType

if TYPE_CHECKING:
    from shared.models.entity import Entity


class ExecutionGapFinding(Base):
    """Rule-based execution gap finding detected by the Execution Gap Engine."""

    __tablename__ = "execution_gap_findings"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    rule_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    rule_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
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
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_record_ids: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
    )
    raw_evidence_refs: Mapped[List[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metric_values: Mapped[Dict[str, Any]] = mapped_column(
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
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="execution_gap_findings",
    )

    __table_args__ = (
        Index("idx_gap_entity_period", "entity_id", "period_start", "period_end"),
        Index("idx_gap_rule", "rule_id", "severity"),
    )


class NegativeSpaceFinding(Base):
    """Absence / omission finding detected by the Negative Space Engine."""

    __tablename__ = "negative_space_findings"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
    )
    check_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    check_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    check_category: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(32),
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
    expected_volume: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    observed_volume: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    drop_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    entropy_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    rationale: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    evidence_record_ids: Mapped[List[str]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        server_default="[]",
    )
    raw_evidence_refs: Mapped[List[Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=list,
        server_default="[]",
    )
    metric_values: Mapped[Dict[str, Any]] = mapped_column(
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
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="negative_space_findings",
    )

    __table_args__ = (
        Index("idx_neg_entity_period", "entity_id", "period_start", "period_end"),
        Index("idx_neg_check", "check_id"),
    )
