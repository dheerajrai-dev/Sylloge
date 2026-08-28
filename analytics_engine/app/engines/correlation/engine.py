"""Correlation Engine coordinating repeat alert burst clustering and text similarity."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from shared.logging import logger
from ..execution_gap.interpreter import LogicInterpreter
from .burst_clusterer import SameAssetBurstClusterer
from .models import BurstCluster, CorrelationDraft
from .text_similarity import NoteSimilarityAnalyzer


class CorrelationEngine:
    """Discovers repeat-asset alert bursts and copy-pasted investigation note clones."""

    def __init__(
        self,
        burst_clusterer: Optional[SameAssetBurstClusterer] = None,
        note_analyzer: Optional[NoteSimilarityAnalyzer] = None,
    ):
        self.burst_clusterer = burst_clusterer or SameAssetBurstClusterer()
        self.note_analyzer = note_analyzer or NoteSimilarityAnalyzer()

    def run(
        self,
        events: List[Any],
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> Tuple[List[CorrelationDraft], List[BurstCluster]]:
        """
        Runs repeat-asset clustering and note similarity analysis.
        Returns:
            (correlations: List[CorrelationDraft], clusters: List[BurstCluster])
        """
        all_correlations: List[CorrelationDraft] = []
        all_clusters: List[BurstCluster] = []

        valid_events = [e for e in (events or []) if e is not None and (isinstance(e, dict) or hasattr(e, "__dict__"))]
        if not valid_events:
            return all_correlations, all_clusters

        # Group events
        alerts = []
        investigations = []

        for ev in valid_events:
            ds_type = str(LogicInterpreter.extract_field_value(ev, "dataset_type") or "")
            std_type = str(LogicInterpreter.extract_field_value(ev, "standard_event_type") or "")

            if ds_type == "alert_metadata" or std_type == "ALERT":
                alerts.append(ev)
            elif ds_type == "investigation_records" or std_type == "INVESTIGATION":
                investigations.append(ev)

        # 1. Repeat-Asset Burst Clustering
        try:
            clusters, burst_corrs = self.burst_clusterer.find_bursts(alerts, entity_id)
            all_clusters.extend(clusters)
            all_correlations.extend(burst_corrs)
        except Exception as exc:
            logger.error(f"Error in Same-Asset Burst Clusterer: {exc}", exc_info=True)

        # 2. Text Similarity Analysis
        try:
            note_corrs = self.note_analyzer.find_similar_notes(investigations, entity_id)
            all_correlations.extend(note_corrs)
        except Exception as exc:
            logger.error(f"Error in Note Similarity Analyzer: {exc}", exc_info=True)

        logger.info(
            f"Correlation Engine generated {len(all_correlations)} correlations and "
            f"{len(all_clusters)} clusters for entity {entity_id}"
        )
        return all_correlations, all_clusters
