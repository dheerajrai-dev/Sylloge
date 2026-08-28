"""Peer Benchmarking Engine package."""

from .cohort import INDUSTRY_BASELINES, get_industry_baseline
from .engine import PeerBenchmarkEngine
from .metrics import extract_entity_metrics
from .models import EntityMetricSnapshot, EntityPeerEvaluation, PeerBenchmarkDraft
from .stats import compute_cohort_distribution, compute_ecdf_percentile, compute_z_score

__all__ = [
    "PeerBenchmarkEngine",
    "extract_entity_metrics",
    "compute_cohort_distribution",
    "compute_z_score",
    "compute_ecdf_percentile",
    "EntityMetricSnapshot",
    "EntityPeerEvaluation",
    "PeerBenchmarkDraft",
    "get_industry_baseline",
    "INDUSTRY_BASELINES",
]
