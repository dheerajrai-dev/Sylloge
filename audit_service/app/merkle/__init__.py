"""Merkle tree calculation helpers and deterministic record hashing for audit service."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from shared.models.correlation import Correlation
from shared.models.event import NormalizedEvent
from shared.models.finding import ExecutionGapFinding, NegativeSpaceFinding
from shared.models.quarantine import QuarantinedRow
from shared.models.risk_score import RiskScore
from shared.models.submission import RawSubmission
from shared.schemas.audit import (
    FindingsComponentSummary,
    ManifestComponentsDTO,
    MerkleSubtreesDTO,
    MerkleTreeDTO,
    NormalizedComponentSummary,
    QuarantineComponentSummary,
    RawSubmissionComponent,
)
from shared.storage.merkle import MerkleTree, sha256_hash_json


def hash_raw_submissions(
    submissions: List[RawSubmission],
) -> Tuple[str, List[RawSubmissionComponent]]:
    """Hashes raw submissions into component objects and computes the subtree Merkle root."""
    components: List[RawSubmissionComponent] = []
    leaves: List[str] = []

    for sub in sorted(submissions, key=lambda s: str(s.submission_id)):
        comp = RawSubmissionComponent(
            submission_id=str(sub.submission_id),
            file_name=sub.file_name,
            sha256_hash=sub.sha256_hash,
            row_count=sub.row_count,
            minio_path=sub.minio_raw_path,
        )
        components.append(comp)
        leaves.append(sha256_hash_json(comp.model_dump()))

    tree = MerkleTree(leaves)
    return tree.root_hash, components


def hash_quarantined_rows(
    rows: List[QuarantinedRow],
) -> Tuple[str, QuarantineComponentSummary]:
    """Hashes quarantined rows and computes the subtree Merkle root."""
    leaves: List[str] = []

    for row in sorted(rows, key=lambda r: (str(r.submission_id), r.row_index)):
        item = {
            "quarantine_id": str(row.quarantine_id),
            "submission_id": str(row.submission_id),
            "row_index": row.row_index,
            "failure_reason": row.failure_reason,
            "failed_fields": sorted(row.failed_fields or []),
            "raw_content": row.raw_content,
        }
        leaves.append(sha256_hash_json(item))

    tree = MerkleTree(leaves)
    subtree_root = tree.root_hash
    summary = QuarantineComponentSummary(
        total_quarantined=len(rows),
        sha256_digest=subtree_root,
    )
    return subtree_root, summary


def hash_normalized_events(
    events: List[NormalizedEvent],
) -> Tuple[str, NormalizedComponentSummary]:
    """Hashes normalized canonical events and computes the subtree Merkle root."""
    leaves: List[str] = []

    for evt in sorted(events, key=lambda e: str(e.event_id)):
        ts_str = evt.event_timestamp.isoformat() if evt.event_timestamp else None
        item = {
            "event_id": str(evt.event_id),
            "submission_id": str(evt.submission_id) if evt.submission_id else None,
            "dataset_type": str(evt.dataset_type),
            "standard_event_type": str(evt.standard_event_type),
            "event_timestamp": ts_str,
            "asset_id": evt.asset_id,
            "action": evt.action,
            "status": evt.status,
            "severity": str(evt.severity) if evt.severity else None,
            "raw_ref_id": evt.raw_ref_id,
            "normalized_payload": evt.normalized_payload,
        }
        leaves.append(sha256_hash_json(item))

    tree = MerkleTree(leaves)
    subtree_root = tree.root_hash
    summary = NormalizedComponentSummary(
        total_events=len(events),
        sha256_digest=subtree_root,
    )
    return subtree_root, summary


def hash_findings_and_scores(
    gap_findings: List[ExecutionGapFinding],
    neg_findings: List[NegativeSpaceFinding],
    correlations: List[Correlation],
    risk_scores: List[RiskScore],
) -> Tuple[str, FindingsComponentSummary]:
    """Hashes gap findings, negative space anomalies, correlations, and risk scores."""
    leaves: List[str] = []

    for gf in sorted(gap_findings, key=lambda f: str(f.finding_id)):
        evidence_ids = sorted([str(eid) for eid in (gf.evidence_record_ids or [])])
        item = {
            "component": "execution_gap",
            "finding_id": str(gf.finding_id),
            "rule_id": gf.rule_id,
            "severity": str(gf.severity),
            "metric_values": gf.metric_values,
            "evidence_record_ids": evidence_ids,
        }
        leaves.append(sha256_hash_json(item))

    for nf in sorted(neg_findings, key=lambda f: str(f.finding_id)):
        item = {
            "component": "negative_space",
            "finding_id": str(nf.finding_id),
            "check_id": nf.check_id,
            "severity": str(nf.severity),
            "expected_volume": round(nf.expected_volume, 4),
            "observed_volume": round(nf.observed_volume, 4),
            "drop_percentage": round(nf.drop_percentage, 4),
            "entropy_score": round(nf.entropy_score, 4) if nf.entropy_score is not None else None,
        }
        leaves.append(sha256_hash_json(item))

    for corr in sorted(correlations, key=lambda c: str(c.correlation_id)):
        item = {
            "component": "correlation",
            "correlation_id": str(corr.correlation_id),
            "correlation_type": corr.correlation_type,
            "primary_event_id": str(corr.primary_event_id),
            "correlated_event_id": str(corr.correlated_event_id),
            "similarity_score": round(corr.similarity_score, 4),
        }
        leaves.append(sha256_hash_json(item))

    for rs in sorted(risk_scores, key=lambda r: str(r.score_id)):
        item = {
            "component": "risk_score",
            "score_id": str(rs.score_id),
            "composite_risk_score": round(rs.composite_risk_score, 4),
            "execution_gap_score": round(rs.execution_gap_score, 4),
            "negative_space_score": round(rs.negative_space_score, 4),
            "peer_deviation_score": round(rs.peer_deviation_score, 4),
        }
        leaves.append(sha256_hash_json(item))

    tree = MerkleTree(leaves)
    subtree_root = tree.root_hash

    latest_composite_score = risk_scores[-1].composite_risk_score if risk_scores else None
    summary = FindingsComponentSummary(
        execution_gap_count=len(gap_findings),
        negative_space_count=len(neg_findings),
        correlations_count=len(correlations),
        composite_risk_score=latest_composite_score,
        sha256_digest=subtree_root,
    )
    return subtree_root, summary


def compute_manifest_merkle_tree(
    raw_subtrees_sha: str,
    quarantine_subtrees_sha: str,
    normalized_subtrees_sha: str,
    findings_subtrees_sha: str,
) -> MerkleTreeDTO:
    """Computes the overall Merkle tree container with the composite root."""
    subtrees = MerkleSubtreesDTO(
        raw_submissions_sha256=raw_subtrees_sha,
        quarantined_records_sha256=quarantine_subtrees_sha,
        normalized_events_sha256=normalized_subtrees_sha,
        findings_and_scores_sha256=findings_subtrees_sha,
    )
    root_sha256 = MerkleTree.compute_composite_manifest_root(
        raw_submissions_sha256=raw_subtrees_sha,
        quarantined_records_sha256=quarantine_subtrees_sha,
        normalized_events_sha256=normalized_subtrees_sha,
        findings_and_scores_sha256=findings_subtrees_sha,
    )
    return MerkleTreeDTO(
        root_sha256=root_sha256,
        subtrees=subtrees,
    )
