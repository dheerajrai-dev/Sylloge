"""Negative Space Engine package."""

from .engine import NegativeSpaceEngine
from .models import CheckDefinition, NegativeSpaceFindingDraft
from .registry import NegativeSpaceCheckRegistry
from .stats import (
    compute_ewma_baseline,
    compute_inter_arrival_cv,
    compute_low_volume_degradation,
    compute_shannon_entropy,
    detect_ewma_volume_cliff,
)

__all__ = [
    "NegativeSpaceEngine",
    "NegativeSpaceCheckRegistry",
    "CheckDefinition",
    "NegativeSpaceFindingDraft",
    "compute_ewma_baseline",
    "detect_ewma_volume_cliff",
    "compute_shannon_entropy",
    "compute_inter_arrival_cv",
    "compute_low_volume_degradation",
]
