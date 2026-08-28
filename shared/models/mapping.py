"""Field mapping profile model for entity-specific data normalization."""

import uuid
from typing import TYPE_CHECKING, Any, Dict
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID, JSONType, TimestampMixin

if TYPE_CHECKING:
    from shared.models.entity import Entity


class FieldMappingProfile(Base, TimestampMixin):
    """Mapping configuration mapping entity-specific columns to standard event fields."""

    __tablename__ = "field_mapping_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(
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
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    mapping_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
    )
    transform_rules: Mapped[Dict[str, Any]] = mapped_column(
        JSONType,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="mapping_profiles",
    )

    __table_args__ = (
        UniqueConstraint("entity_id", "dataset_type", "version", name="uq_entity_dataset_version"),
        Index("idx_fmp_entity_dataset", "entity_id", "dataset_type", "is_active"),
    )
