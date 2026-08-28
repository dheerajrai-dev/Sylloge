"""Statistical calculations for Peer Benchmarking."""

import math
from typing import Dict, List, Tuple
import numpy as np


def compute_cohort_distribution(values: List[float]) -> Tuple[float, float, float, float, float, float]:
    """
    Computes sample mean, stddev, p25, p50, p75, p90.
    Returns:
        (mean, std_dev, p25, p50, p75, p90)
    """
    if not values:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    arr = np.array(values, dtype=float)
    n = len(arr)

    mean_val = float(np.mean(arr))
    if n > 1:
        std_val = float(np.std(arr, ddof=1))
    else:
        std_val = 0.0

    # Ensure std_val is at least 1e-4 to prevent division by zero
    std_val = max(std_val, 1e-4)

    p25 = float(np.percentile(arr, 25))
    p50 = float(np.percentile(arr, 50))
    p75 = float(np.percentile(arr, 75))
    p90 = float(np.percentile(arr, 90))

    return (
        round(mean_val, 4),
        round(std_val, 4),
        round(p25, 4),
        round(p50, 4),
        round(p75, 4),
        round(p90, 4),
    )


def compute_z_score(value: float, mean: float, std_dev: float) -> float:
    """Computes Z-Score = (x - mu) / sigma."""
    sigma = max(std_dev, 1e-4)
    z = (value - mean) / sigma
    return round(float(z), 4)


def compute_ecdf_percentile(value: float, cohort_values: List[float]) -> float:
    """
    Computes Percentile Rank via ECDF with tie-breaking:
    Percentile(x) = (sum(1[x_j < x]) + 0.5 * sum(1[x_j == x])) / N * 100
    """
    if not cohort_values:
        return 50.0

    n = len(cohort_values)
    strict_less = sum(1 for x in cohort_values if x < value)
    equal = sum(1 for x in cohort_values if math.isclose(x, value, rel_tol=1e-5, abs_tol=1e-5))

    pct = ((strict_less + 0.5 * equal) / float(n)) * 100.0
    return round(min(100.0, max(0.0, pct)), 2)
