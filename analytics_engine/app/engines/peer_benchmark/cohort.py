"""Cohort segmentation and reference baselines."""

from typing import Dict, List, Optional
from .models import EntityMetricSnapshot

# Standard calibrated industry baselines (Mean, StdDev) for the 5 metrics
INDUSTRY_BASELINES: Dict[str, Dict[str, tuple]] = {
    "Banking": {
        "mtti_minutes": (30.0, 15.0),
        "escalation_rate": (0.08, 0.03),
        "stale_case_ratio": (0.05, 0.02),
        "coverage_gap_ratio": (0.02, 0.01),
        "execution_gap_rate": (2.0, 1.0),
    },
    "Telecom": {
        "mtti_minutes": (45.0, 20.0),
        "escalation_rate": (0.06, 0.025),
        "stale_case_ratio": (0.08, 0.03),
        "coverage_gap_ratio": (0.05, 0.02),
        "execution_gap_rate": (3.5, 1.5),
    },
    "Energy": {
        "mtti_minutes": (60.0, 25.0),
        "escalation_rate": (0.05, 0.02),
        "stale_case_ratio": (0.10, 0.04),
        "coverage_gap_ratio": (0.04, 0.02),
        "execution_gap_rate": (4.0, 2.0),
    },
    "Healthcare": {
        "mtti_minutes": (50.0, 22.0),
        "escalation_rate": (0.07, 0.03),
        "stale_case_ratio": (0.09, 0.035),
        "coverage_gap_ratio": (0.06, 0.03),
        "execution_gap_rate": (4.5, 2.0),
    },
    "DEFAULT": {
        "mtti_minutes": (45.0, 20.0),
        "escalation_rate": (0.07, 0.03),
        "stale_case_ratio": (0.07, 0.03),
        "coverage_gap_ratio": (0.05, 0.02),
        "execution_gap_rate": (3.0, 1.5),
    },
}


def get_industry_baseline(sector: str, metric_name: str) -> tuple:
    """Returns (mean, std_dev) reference baseline for metric in sector."""
    sec_dict = INDUSTRY_BASELINES.get(sector, INDUSTRY_BASELINES["DEFAULT"])
    return sec_dict.get(metric_name, INDUSTRY_BASELINES["DEFAULT"].get(metric_name, (50.0, 15.0)))
