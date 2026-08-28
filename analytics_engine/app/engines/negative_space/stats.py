"""Statistical calculations for Negative Space Engine."""

from collections import Counter
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def compute_ewma_baseline(series: List[float], alpha: float = 0.20) -> Tuple[float, float]:
    """
    Computes Exponentially Weighted Moving Average (EWMA) mean and variance.
    Recurrence:
        mu_t = alpha * x_t + (1 - alpha) * mu_{t-1}
        var_t = alpha * (x_t - mu_t)^2 + (1 - alpha) * var_{t-1}
    Returns:
        (mu: float, sigma: float)
    """
    if not series:
        return 0.0, 0.0

    mu = float(series[0])
    var = 0.0

    for x in series[1:]:
        x_val = float(x)
        mu = alpha * x_val + (1.0 - alpha) * mu
        var = alpha * ((x_val - mu) ** 2) + (1.0 - alpha) * var

    sigma = math.sqrt(max(0.0, var))
    return mu, sigma


def detect_ewma_volume_cliff(
    daily_volumes: List[float],
    alpha: float = 0.20,
    k: float = 3.0,
    min_history_days: int = 5,
) -> Optional[Dict[str, Any]]:
    """
    Detects sudden telemetry volume drops beyond k * sigma from EWMA baseline.
    Returns anomaly details if cliff is detected, otherwise None.
    """
    if len(daily_volumes) < min_history_days:
        return None

    # Compute baseline on historical window (excluding the latest day)
    history = daily_volumes[:-1]
    latest_volume = float(daily_volumes[-1])

    mu_hist, sigma_hist = compute_ewma_baseline(history, alpha=alpha)

    # Cliff condition: x_t < mu_{t-1} - k * sigma_{t-1}
    cliff_threshold = mu_hist - (k * sigma_hist)

    # Relative drop percentage: ((mu - x) / mu) * 100
    drop_pct = 0.0
    if mu_hist > 0:
        drop_pct = max(0.0, ((mu_hist - latest_volume) / mu_hist) * 100.0)

    is_cliff = (latest_volume < cliff_threshold) or (mu_hist >= 10.0 and drop_pct >= 60.0)

    if is_cliff:
        return {
            "expected_volume": round(mu_hist, 2),
            "observed_volume": round(latest_volume, 2),
            "sigma": round(sigma_hist, 2),
            "drop_percentage": round(drop_pct, 2),
            "cliff_threshold": round(cliff_threshold, 2),
            "history_days": len(history),
        }

    return None


def compute_shannon_entropy(categories: List[str]) -> Tuple[float, float, int, int]:
    """
    Computes Categorical Shannon Entropy H(X) = -sum(p(c_i) * log2(p(c_i))).
    Returns:
        (entropy: float, max_entropy: float, sample_count: int, unique_categories: int)
    """
    if not categories:
        return 0.0, 0.0, 0, 0

    n = len(categories)
    counts = Counter(categories)
    m = len(counts)

    if m <= 1:
        return 0.0, 0.0, n, m

    entropy = 0.0
    for count in counts.values():
        p = count / float(n)
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(m)
    return round(entropy, 4), round(max_entropy, 4), n, m


def compute_inter_arrival_cv(timestamps: List[datetime]) -> Tuple[float, float, float, int]:
    """
    Computes Coefficient of Variation (CV = sigma / mu) for inter-arrival intervals.
    Returns:
        (cv: float, mean_delta_seconds: float, std_delta_seconds: float, sample_count: int)
    """
    if len(timestamps) < 2:
        return 1.0, 0.0, 0.0, len(timestamps)

    sorted_times = sorted(timestamps)
    deltas = []
    for i in range(1, len(sorted_times)):
        delta = (sorted_times[i] - sorted_times[i - 1]).total_seconds()
        deltas.append(max(0.0, delta))

    arr = np.array(deltas, dtype=float)
    mean_val = float(np.mean(arr))
    std_val = float(np.std(arr, ddof=1)) if len(deltas) > 1 else 0.0

    if mean_val <= 0:
        cv = 0.0
    else:
        cv = std_val / mean_val

    return round(cv, 5), round(mean_val, 2), round(std_val, 2), len(timestamps)


def compute_low_volume_degradation(n: int, n_min: int = 15) -> Tuple[float, bool]:
    """
    Low-volume graceful degradation model:
    w_deg = max(0.10, min(1.0, N / N_min))
    Returns:
        (w_deg: float, is_degraded: bool)
    """
    if n >= n_min:
        return 1.0, False

    w_deg = max(0.10, min(1.0, float(n) / float(n_min)))
    return round(w_deg, 4), True
