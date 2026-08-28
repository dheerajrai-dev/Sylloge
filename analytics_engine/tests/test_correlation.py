"""Unit tests for Correlation Engine: Repeat Asset Bursts and Text Similarity."""

from datetime import datetime, timedelta, timezone
import uuid
import pytest

from analytics_engine.engines.correlation.burst_clusterer import SameAssetBurstClusterer
from analytics_engine.engines.correlation.engine import CorrelationEngine
from analytics_engine.engines.correlation.text_similarity import (
    NoteSimilarityAnalyzer,
    compute_jaccard_similarity,
    preprocess_text,
)


def test_text_preprocessing_and_jaccard():
    """Verifies lowercase, punctuation removal, stop-word filtering, and Jaccard."""
    text1 = "The analyst investigated the brute force attempt and confirmed host isolation."
    clean1, tokens1 = preprocess_text(text1)

    assert "the" not in tokens1
    assert "investigated" in tokens1
    assert "brute" in tokens1
    assert "isolation" in tokens1

    text2 = "The analyst investigated the brute force attempt and verified host isolation."
    clean2, tokens2 = preprocess_text(text2)

    jaccard = compute_jaccard_similarity(tokens1, tokens2)
    assert jaccard >= 0.75  # Near clone (6 of 8 unique tokens match)


def test_note_similarity_tfidf_and_jaccard(entity_id: uuid.UUID):
    """Verifies TF-IDF cosine and Jaccard similarity clone detection."""
    analyzer = NoteSimilarityAnalyzer(tfidf_threshold=0.85, jaccard_threshold=0.80, min_tokens=5)

    note_text = (
        "Initial triage completed. Verified user credentials with Active Directory. "
        "User confirmed legitimate login from traveling IP address. No malicious indicators found. Resolving as false positive."
    )

    inv1 = {
        "event_id": uuid.uuid4(),
        "case_id": "CASE-101",
        "analyst_id": "analyst_bob",
        "investigation_notes": note_text,
    }
    inv2 = {
        "event_id": uuid.uuid4(),
        "case_id": "CASE-102",
        "analyst_id": "analyst_alice",
        "investigation_notes": note_text,  # Exact duplicate text
    }
    inv3 = {
        "event_id": uuid.uuid4(),
        "case_id": "CASE-103",
        "analyst_id": "analyst_charlie",
        "investigation_notes": "Malware analysis initiated. Memory dump extracted. C2 beacon detected to external host.",
    }

    correlations = analyzer.find_similar_notes([inv1, inv2, inv3], entity_id)
    assert len(correlations) == 1
    assert correlations[0].correlation_type == "TFIDF_NOTE_SIMILARITY"
    assert correlations[0].similarity_score >= 0.95
    assert correlations[0].shared_attributes["case_id_a"] == "CASE-101"
    assert correlations[0].shared_attributes["case_id_b"] == "CASE-102"


def test_same_asset_burst_clustering(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies same-asset 24h burst clustering with >=5 alerts."""
    clusterer = SameAssetBurstClusterer(window_seconds=86400, repeat_alert_threshold=5)

    alerts = []
    # 6 alerts on SRV-FINANCE-01 within 4 hours
    for i in range(6):
        alerts.append({
            "event_id": uuid.uuid4(),
            "asset_id": "SRV-FINANCE-01",
            "rule_id": f"RULE_00{i % 2}",
            "severity": "MEDIUM",
            "event_timestamp": sample_now - timedelta(hours=4 - i * 0.5),
        })

    clusters, correlations = clusterer.find_bursts(alerts, entity_id)
    assert len(clusters) == 1
    assert clusters[0].asset_id == "SRV-FINANCE-01"
    assert clusters[0].alert_count == 6
    assert len(correlations) == 5  # Primary to each of 5 subsequent alerts


def test_correlation_engine_full_run(entity_id: uuid.UUID, sample_now: datetime):
    """Verifies CorrelationEngine orchestrates both burst and note analyzers."""
    engine = CorrelationEngine()

    note_text = "System alert reviewed and confirmed standard scheduled backup batch process. No action required."
    events = [
        # 5 High alerts on same asset
        *[
            {
                "event_id": uuid.uuid4(),
                "dataset_type": "alert_metadata",
                "standard_event_type": "ALERT",
                "asset_id": "SRV-DB-PROD",
                "severity": "HIGH",
                "event_timestamp": sample_now - timedelta(hours=i),
            }
            for i in range(5)
        ],
        # 2 duplicate investigations across different cases
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "investigation_records",
            "standard_event_type": "INVESTIGATION",
            "case_id": "CASE-A1",
            "investigation_notes": note_text,
        },
        {
            "event_id": uuid.uuid4(),
            "dataset_type": "investigation_records",
            "standard_event_type": "INVESTIGATION",
            "case_id": "CASE-A2",
            "investigation_notes": note_text,
        },
    ]

    corrs, clusters = engine.run(events, entity_id, sample_now - timedelta(days=1), sample_now)
    assert len(clusters) == 1
    assert len(corrs) >= 5  # 4 burst links + 1 note clone link
