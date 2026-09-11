"""Mathematical normalization formulas and tier classification for Risk Scoring."""

import math
from typing import Any, List, Optional


def compute_execution_gap_subscore(
    gap_findings: List[Any],
    alert_count: int = 0,
) -> float:
    """
    Computes Execution Gap sub-score S_EG in [0.0, 100.0]:
    S_EG = min(100.0, sum((sev / 100) * conf * w_type) * (100 / ScaleFactor))
    where ScaleFactor = max(15.0, log10(max(0, alert_count) + 10.0) * 10.0)
    """
    if not gap_findings:
        return 0.0

    scale_factor = max(15.0, math.log10(max(0, alert_count) + 10.0) * 10.0)

    raw_sum = 0.0
    for f in gap_findings:
        sev = getattr(f, "severity_score", 70) if hasattr(f, "severity_score") else 70
        conf = getattr(f, "confidence", 0.90) if hasattr(f, "confidence") else 0.90
        w_type = 1.0

        raw_sum += (float(sev) / 100.0) * float(conf) * w_type

    sub_score = (raw_sum * (100.0 / scale_factor))
    return round(min(100.0, max(0.0, sub_score)), 2)


def compute_negative_space_subscore(
    negative_space_findings: List[Any],
) -> float:
    """
    Computes Negative Space sub-score S_NS in [0.0, 100.0]:
    S_NS = min(100.0, sum((sev / 100) * conf * w_deg * 20.0))
    """
    if not negative_space_findings:
        return 0.0

    raw_sum = 0.0
    for f in negative_space_findings:
        sev = getattr(f, "severity_score", 80) if hasattr(f, "severity_score") else 80
        conf = getattr(f, "confidence", 0.90) if hasattr(f, "confidence") else 0.90
        w_deg = getattr(f, "degradation_factor", 1.0) if hasattr(f, "degradation_factor") else 1.0

        raw_sum += (float(sev) / 100.0) * float(conf) * float(w_deg) * 20.0

    return round(min(100.0, max(0.0, raw_sum)), 2)


def compute_composite_risk_score(
    s_eg: float,
    s_ns: float,
    s_peer: float,
    w_eg: float = 0.45,
    w_ns: float = 0.35,
    w_peer: float = 0.20,
) -> float:
    """
    Computes weighted composite risk score in [0.0, 100.0]:
    Composite = w_eg * S_EG + w_ns * S_NS + w_peer * S_Peer
    """
    comp = (w_eg * s_eg) + (w_ns * s_ns) + (w_peer * s_peer)
    return round(min(100.0, max(0.0, comp)), 2)


def map_score_to_risk_tier(score: float) -> str:
    """
    Maps 0-100 score to 4 supervisory risk bands:
    - LOW: 0.0 - 25.0
    - GUARDED: 25.01 - 50.0
    - ELEVATED: 50.01 - 75.0
    - CRITICAL: 75.01 - 100.0
    """
    if score <= 25.0:
        return "LOW"
    elif score <= 50.0:
        return "GUARDED"
    elif score <= 75.0:
        return "ELEVATED"
    return "CRITICAL"


def determine_trend_direction(current_score: float, previous_score: Optional[float]) -> str:
    """
    Determines trend direction:
    - IMPROVING if current < prev - 2.0
    - DETERIORATING if current > prev + 2.0
    - STABLE otherwise
    """
    if previous_score is None:
        return "STABLE"

    delta = current_score - previous_score
    if delta > 2.0:
        return "DETERIORATING"
    elif delta < -2.0:
        return "IMPROVING"
    return "STABLE"
