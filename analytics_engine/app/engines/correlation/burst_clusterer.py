"""Same-asset 24h burst clustering."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid

from shared.logging import logger
from ..execution_gap.interpreter import LogicInterpreter
from .models import BurstCluster, CorrelationDraft


class SameAssetBurstClusterer:
    """Clusters repeat alerts on the same asset within sliding 24h windows."""

    def __init__(
        self,
        window_seconds: int = 86400,  # 24 hours
        repeat_alert_threshold: int = 5,
        repeat_high_alert_threshold: int = 3,
    ):
        self.window_seconds = window_seconds
        self.repeat_alert_threshold = repeat_alert_threshold
        self.repeat_high_alert_threshold = repeat_high_alert_threshold

    def find_bursts(
        self,
        alerts: List[Any],
        entity_id: uuid.UUID,
    ) -> Tuple[List[BurstCluster], List[CorrelationDraft]]:
        """
        Groups alerts by asset_id and identifies 24-hour bursts.
        Returns:
            (clusters: List[BurstCluster], correlations: List[CorrelationDraft])
        """
        clusters: List[BurstCluster] = []
        correlations: List[CorrelationDraft] = []

        if not alerts:
            return clusters, correlations

        # Group alerts by asset_id
        alerts_by_asset = defaultdict(list)
        for a in alerts:
            aid = LogicInterpreter.extract_field_value(a, "asset_id")
            if aid and str(aid).strip() and str(aid).strip().lower() != "none":
                alerts_by_asset[str(aid).strip()].append(a)

        for asset_id, asset_alerts in alerts_by_asset.items():
            if len(asset_alerts) < min(self.repeat_alert_threshold, self.repeat_high_alert_threshold):
                continue

            # Sort alerts by event_timestamp
            asset_alerts.sort(
                key=lambda x: (LogicInterpreter.extract_field_value(x, "event_timestamp") or datetime.min.replace(tzinfo=timezone.utc))
            )

            # Sliding window over alerts
            i = 0
            n = len(asset_alerts)
            while i < n:
                t_start = LogicInterpreter.extract_field_value(asset_alerts[i], "event_timestamp")
                if not t_start:
                    i += 1
                    continue

                window_alerts = [asset_alerts[i]]
                high_crit_count = 1 if str(LogicInterpreter.extract_field_value(asset_alerts[i], "severity") or "").upper() in ("CRITICAL", "HIGH") else 0

                j = i + 1
                while j < n:
                    t_curr = LogicInterpreter.extract_field_value(asset_alerts[j], "event_timestamp")
                    if not t_curr:
                        j += 1
                        continue

                    delta_sec = (t_curr - t_start).total_seconds()
                    if delta_sec <= self.window_seconds:
                        window_alerts.append(asset_alerts[j])
                        sev = str(LogicInterpreter.extract_field_value(asset_alerts[j], "severity") or "").upper()
                        if sev in ("CRITICAL", "HIGH"):
                            high_crit_count += 1
                        j += 1
                    else:
                        break

                total_count = len(window_alerts)
                is_burst = (total_count >= self.repeat_alert_threshold) or (high_crit_count >= self.repeat_high_alert_threshold)

                if is_burst:
                    t_end = LogicInterpreter.extract_field_value(window_alerts[-1], "event_timestamp") or t_start
                    rules = list({
                        str(LogicInterpreter.extract_field_value(a, "rule_id") or LogicInterpreter.extract_field_value(a, "action") or "Alert")
                        for a in window_alerts
                    })

                    evidence_uuids = []
                    for a in window_alerts:
                        eid = LogicInterpreter.extract_field_value(a, "event_id")
                        if eid:
                            evidence_uuids.append(str(eid))

                    cluster_id = uuid.uuid4()
                    cluster = BurstCluster(
                        cluster_id=cluster_id,
                        entity_id=entity_id,
                        asset_id=asset_id,
                        alert_count=total_count,
                        high_critical_count=high_crit_count,
                        distinct_rules=rules,
                        time_window_start=t_start,
                        time_window_end=t_end,
                        evidence_record_ids=evidence_uuids,
                    )
                    clusters.append(cluster)

                    # Build pairwise correlation links from primary (first alert) to subsequent alerts
                    primary_event = window_alerts[0]
                    prim_id_raw = LogicInterpreter.extract_field_value(primary_event, "event_id")
                    prim_uuid = uuid.UUID(str(prim_id_raw)) if prim_id_raw else uuid.uuid4()

                    for subsequent in window_alerts[1:]:
                        corr_id_raw = LogicInterpreter.extract_field_value(subsequent, "event_id")
                        corr_uuid = uuid.UUID(str(corr_id_raw)) if corr_id_raw else uuid.uuid4()

                        if prim_uuid == corr_uuid:
                            continue

                        corr_draft = CorrelationDraft(
                            entity_id=entity_id,
                            correlation_type="REPEAT_ASSET_ALERT",
                            primary_event_id=prim_uuid,
                            correlated_event_id=corr_uuid,
                            asset_id=asset_id,
                            similarity_score=1.0,
                            shared_attributes={
                                "cluster_id": str(cluster_id),
                                "burst_alert_count": total_count,
                                "high_critical_count": high_crit_count,
                                "distinct_rules": rules,
                                "window_hours": round(self.window_seconds / 3600.0, 1),
                            },
                            rationale=(
                                f"Same-asset alert burst on {asset_id}: {total_count} alerts fired within 24h "
                                f"({high_crit_count} High/Critical), indicating persistent unmitigated root cause."
                            ),
                        )
                        correlations.append(corr_draft)

                    # Jump window forward past this cluster
                    i = j
                else:
                    i += 1

        return clusters, correlations
