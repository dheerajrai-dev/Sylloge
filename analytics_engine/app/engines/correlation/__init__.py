"""Correlation Engine package."""

from .burst_clusterer import SameAssetBurstClusterer
from .engine import CorrelationEngine
from .models import BurstCluster, CorrelationDraft
from .text_similarity import NoteSimilarityAnalyzer, compute_jaccard_similarity, preprocess_text

__all__ = [
    "CorrelationEngine",
    "SameAssetBurstClusterer",
    "NoteSimilarityAnalyzer",
    "CorrelationDraft",
    "BurstCluster",
    "preprocess_text",
    "compute_jaccard_similarity",
]
