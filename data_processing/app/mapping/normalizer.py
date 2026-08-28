"""Canonical event normalizer producing NormalizedEvent ORM models from validated parsed rows."""

import datetime
import uuid
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from shared.events.enums import DatasetType
from shared.models.event import NormalizedEvent
from shared.models.mapping import FieldMappingProfile
from .engine import FieldMappingEngine


class CanonicalNormalizer:
    """Normalizes raw validated rows and produces NormalizedEvent database records."""

    def __init__(
        self,
        submission_id: uuid.UUID,
        entity_id: uuid.UUID,
        dataset_type: Union[DatasetType, str],
        mapping_profile: Optional[FieldMappingProfile] = None,
    ):
        self.submission_id = submission_id
        self.entity_id = entity_id
        self.dataset_type = dataset_type if isinstance(dataset_type, str) else dataset_type.value
        self.mapping_profile = mapping_profile
        self.engine = FieldMappingEngine(self.dataset_type, mapping_profile)
        self.normalized_events: List[NormalizedEvent] = []

    def normalize_row(self, raw_data: Dict[str, Any], row_index: int) -> NormalizedEvent:
        """Transforms a single raw row into a NormalizedEvent model."""
        norm = self.engine.normalize_record(raw_data, row_index)
        event_model = NormalizedEvent(
            event_id=uuid.uuid4(),
            submission_id=self.submission_id,
            entity_id=self.entity_id,
            dataset_type=norm["dataset_type"],
            standard_event_type=norm["standard_event_type"],
            event_timestamp=norm["event_timestamp"],
            asset_id=norm["asset_id"],
            user_id=norm["user_id"],
            action=norm["action"],
            status=norm["status"],
            severity=norm["severity"],
            source_ip=norm["source_ip"],
            destination_ip=norm["destination_ip"],
            raw_row_index=norm["raw_row_index"],
            raw_ref_id=norm["raw_ref_id"],
            normalized_payload=norm["normalized_payload"],
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        self.normalized_events.append(event_model)
        return event_model

    @property
    def total_normalized(self) -> int:
        return len(self.normalized_events)

    def save_to_sync_db(self, session: Session) -> int:
        """Persists normalized events in database using synchronous session."""
        if not self.normalized_events:
            return 0
        session.add_all(self.normalized_events)
        session.flush()
        return len(self.normalized_events)

    async def save_to_async_db(self, session: AsyncSession) -> int:
        """Persists normalized events in database using asynchronous session."""
        if not self.normalized_events:
            return 0
        session.add_all(self.normalized_events)
        await session.flush()
        return len(self.normalized_events)
