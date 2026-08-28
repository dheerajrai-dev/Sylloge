"""Dataset catalog model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.base import Base, GUID

if TYPE_CHECKING:
    from shared.models.entity import Entity


class Dataset(Base):
    """Dataset catalog metadata for supervised entities."""

    __tablename__ = "datasets"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
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
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    schema_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="1.0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="datasets",
    )

    __table_args__ = (
        Index("idx_datasets_entity_type", "entity_id", "dataset_type"),
    )
