"""Explainability Engine implementation."""

from typing import Any, Dict, List, Optional
import uuid

from shared.logging import logger
from .card_builder import RationaleCardBuilder
from .models import RationaleCardData


class ExplainabilityEngine:
    """Generates forensic Rationale Cards for all platform findings."""

    def __init__(self, builder: Optional[RationaleCardBuilder] = None):
        self.builder = builder or RationaleCardBuilder()

    def generate_cards(
        self,
        entity_id: uuid.UUID,
        execution_gap_findings: List[Any],
        negative_space_findings: List[Any],
        events: Optional[List[Any]] = None,
    ) -> List[RationaleCardData]:
        """Generates structured Rationale Cards with complete forensic evidence tracing."""
        cards: List[RationaleCardData] = []

        # Index events by event_id for fast lookup
        events_map: Dict[str, Any] = {}
        if events:
            for ev in events:
                eid = getattr(ev, "event_id", None)
                if eid:
                    events_map[str(eid)] = ev

        # 1. Cards for Execution Gap Findings
        for eg_finding in execution_gap_findings:
            try:
                card = self.builder.build_from_execution_gap(
                    finding=eg_finding,
                    entity_id=entity_id,
                    events_map=events_map,
                )
                cards.append(card)
            except Exception as exc:
                logger.error(f"Error generating Rationale Card for Execution Gap finding: {exc}", exc_info=True)

        # 2. Cards for Negative Space Findings
        for ns_finding in negative_space_findings:
            try:
                card = self.builder.build_from_negative_space(
                    finding=ns_finding,
                    entity_id=entity_id,
                    events_map=events_map,
                )
                cards.append(card)
            except Exception as exc:
                logger.error(f"Error generating Rationale Card for Negative Space finding: {exc}", exc_info=True)

        logger.info(f"Explainability Engine generated {len(cards)} Rationale Cards for entity {entity_id}")
        return cards
