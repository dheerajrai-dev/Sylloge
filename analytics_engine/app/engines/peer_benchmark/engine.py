"""Peer Benchmarking Engine implementation with fallback hierarchy and dampening."""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from shared.logging import logger
from .cohort import get_industry_baseline
from .metrics import extract_entity_metrics
from .models import EntityMetricSnapshot, EntityPeerEvaluation, PeerBenchmarkDraft
from .stats import compute_cohort_distribution, compute_ecdf_percentile, compute_z_score

METRIC_NAMES = [
    "mtti_minutes",
    "escalation_rate",
    "stale_case_ratio",
    "coverage_gap_ratio",
    "execution_gap_rate",
]


class PeerBenchmarkEngine:
    """Evaluates entity metrics against sector and size-tier peer cohorts."""

    def __init__(self, min_peer_group_size: int = 3, dampening_lambda: float = 0.50):
        self.min_peer_group_size = min_peer_group_size
        self.dampening_lambda = dampening_lambda

    def evaluate_entity(
        self,
        target_entity_id: uuid.UUID,
        sector: str,
        size_tier: str,
        target_events: List[Any],
        execution_gap_findings: Optional[List[Any]] = None,
        peer_snapshots: Optional[List[EntityMetricSnapshot]] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> Tuple[EntityPeerEvaluation, List[PeerBenchmarkDraft]]:
        """
        Extracts target entity metrics, cohorts peers, computes Z-scores, percentiles,
        and applies low-confidence fallback if peer cohort size < min_peer_group_size.
        """
        now = datetime.now(datetime.timezone.utc if hasattr(datetime, 'timezone') else None)
        p_start = period_start or now
        p_end = period_end or now

        # 1. Extract target entity metrics
        target_snapshot = extract_entity_metrics(
            entity_id=target_entity_id,
            sector=sector,
            size_tier=size_tier,
            events=target_events,
            execution_gap_findings=execution_gap_findings,
        )

        all_snapshots = list(peer_snapshots or [])
        # Ensure target snapshot is included
        if not any(s.entity_id == target_entity_id for s in all_snapshots):
            all_snapshots.append(target_snapshot)

        # 2. Determine cohort peers with fallback hierarchy
        # Level 1: Exact cohort (same sector and size_tier)
        exact_peers = [s for s in all_snapshots if s.sector.lower() == sector.lower() and s.size_tier.lower() == size_tier.lower()]
        
        cohort_peers = exact_peers
        fallback_applied = "EXACT_COHORT"
        is_low_confidence = False
        dampening_factor = 1.0

        if len(exact_peers) < self.min_peer_group_size:
            is_low_confidence = True
            dampening_factor = self.dampening_lambda

            # Level 2: Sector-wide cohort
            sector_peers = [s for s in all_snapshots if s.sector.lower() == sector.lower()]
            if len(sector_peers) >= self.min_peer_group_size:
                cohort_peers = sector_peers
                fallback_applied = "SECTOR_FALLBACK"
            else:
                # Level 3: Global cross-sector cohort
                if len(all_snapshots) >= self.min_peer_group_size:
                    cohort_peers = all_snapshots
                    fallback_applied = "GLOBAL_FALLBACK"
                else:
                    # Level 4: Baseline Reference Fallback
                    cohort_peers = all_snapshots
                    fallback_applied = "BASELINE_FALLBACK"

        peer_group_size = len(cohort_peers)

        # 3. Compute distributions and benchmarks for each metric
        benchmarks: List[PeerBenchmarkDraft] = []
        z_scores: Dict[str, float] = {}
        percentiles: Dict[str, float] = {}
        risk_z_list: List[float] = []

        for metric_name in METRIC_NAMES:
            target_val = getattr(target_snapshot, metric_name, 0.0)
            cohort_vals = [getattr(s, metric_name, 0.0) for s in cohort_peers]

            if fallback_applied == "BASELINE_FALLBACK" or len(cohort_vals) < 2:
                base_mu, base_sigma = get_industry_baseline(sector, metric_name)
                mean_val = base_mu
                std_dev = base_sigma
                p25 = base_mu - 0.67 * base_sigma
                p50 = base_mu
                p75 = base_mu + 0.67 * base_sigma
                p90 = base_mu + 1.28 * base_sigma
            else:
                mean_val, std_dev, p25, p50, p75, p90 = compute_cohort_distribution(cohort_vals)

            z = compute_z_score(target_val, mean_val, std_dev)
            pct = compute_ecdf_percentile(target_val, cohort_vals if len(cohort_vals) >= 2 else [mean_val])

            z_scores[metric_name] = z
            percentiles[metric_name] = pct

            # Risk direction: for escalation_rate, lower is higher risk (-z)
            if metric_name == "escalation_rate":
                risk_z = -z
            else:
                risk_z = z
            risk_z_list.append(risk_z)

            benchmarks.append(
                PeerBenchmarkDraft(
                    sector=sector,
                    size_tier=size_tier,
                    metric_name=metric_name,
                    period_start=p_start,
                    period_end=p_end,
                    peer_group_size=peer_group_size,
                    mean_val=mean_val,
                    std_dev=std_dev,
                    p25=p25,
                    p50=p50,
                    p75=p75,
                    p90=p90,
                    is_low_confidence=is_low_confidence,
                    fallback_level=fallback_applied,
                )
            )

        # 4. Compute composite peer deviation score
        mean_risk_z = float(sum(risk_z_list) / len(risk_z_list)) if risk_z_list else 0.0
        # S_Peer = min(100.0, max(0.0, 50.0 + (25.0 * mean_risk_z * dampening_factor)))
        raw_peer_score = 50.0 + (25.0 * mean_risk_z * dampening_factor)
        peer_score = min(100.0, max(0.0, round(raw_peer_score, 2)))

        evaluation = EntityPeerEvaluation(
            entity_id=target_entity_id,
            sector=sector,
            size_tier=size_tier,
            period_start=p_start,
            period_end=p_end,
            peer_group_size=peer_group_size,
            is_low_confidence=is_low_confidence,
            fallback_applied=fallback_applied,
            dampening_factor=dampening_factor,
            metric_z_scores=z_scores,
            metric_percentiles=percentiles,
            mean_risk_z_score=round(mean_risk_z, 4),
            peer_deviation_score=peer_score,
        )

        logger.info(
            f"Peer Benchmark evaluated for entity {target_entity_id} in ({sector}, {size_tier}): "
            f"peers={peer_group_size}, low_conf={is_low_confidence}, score={peer_score}"
        )
        return evaluation, benchmarks
