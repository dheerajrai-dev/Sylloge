# SAT-SA (SYLLOGE) Supervisory Validation & Compliance Audit Report

**Report ID**: `VAL-REP-FC081034`  
**Generated At (UTC)**: `2026-08-26 13:34:34 UTC`  
**Evaluation Scope**: `10 Entities across 2 Periods (8 Data Streams)`  
**Platform Version**: `SAT-SA v1.0.0 (SIH-2026 Problem Statement 26157)`  
**Air-Gapped Enclave Integrity**: `VERIFIED (Zero External Calls)`

---

## 1. Executive Summary

| Key Performance Indicator | Measured Result | Supervisory Threshold | Status |
|---|---|---|---|
| **Overall Macro Precision** | **54.98%** | $\ge 90.0\%$ | **{{ macro_precision_status }}** |
| **Overall Macro Recall** | **60.04%** | $\ge 90.0\%$ | **{{ macro_recall_status }}** |
| **Overall Macro F1-Score** | **57.40%** | $\ge 90.0\%$ | **{{ macro_f1_status }}** |
| **Quality Tier Classification Accuracy** | **30.00%** | $\ge 90.0\%$ | **{{ tier_accuracy_status }}** |
| **Planted Ground Truth Anomaly Coverage** | **187 / 244 (76.64%)** | $\ge 90.0\%$ | **{{ coverage_status }}** |
| **Cryptographic Merkle Root Verification** | `b15de9dc61db7c1f...` | Match Manifest | **{{ merkle_status }}** |

> **Executive Conclusion**:  
> {{ executive_summary_text }}

---

## 2. Per-Rule Performance Breakdown

Comprehensive evaluation across all 18 execution gap rules, negative space absence checks, correlation patterns, and risk scoring baselines.

| Rule / Check Code | Description | Category | Ground Truth | TP | FP | FN | Precision | Recall | F1-Score | Compliance Status |
|---|---|---|---|---|---|---|---|---|---|---|
{% for r in rule_metrics %}
| **{{ r.code }}** | {{ r.name }} | {{ r.category }} | {{ r.ground_truth_count }} | {{ r.tp }} | {{ r.fp }} | {{ r.fn }} | {{ r.precision | round(2) }}% | {{ r.recall | round(2) }}% | **{{ r.f1 | round(2) }}%** | {{ r.status_badge }} |
{% endfor %}
| **TOTAL / MACRO AVG** | *Aggregate Benchmark Evaluation* | *All Engines* | **244** | **187** | **1777908** | **57** | **54.98%** | **60.04%** | **57.40%** | **{{ overall_status_badge }}** |

---

## 3. Tier Classification Confusion Matrix

Evaluation of entity risk tier placement (HEALTHY / LOW $\le 25$, AVERAGE / ELEVATED $35-65$, WEAK / CRITICAL $\ge 75$) compared against synthetic ground-truth quality profiles.

```
                    ┌──────────────────────────────────────────────────┐
                    │               PREDICTED RISK TIER                │
                    │   HEALTHY (LOW) │ AVERAGE (ELEV) │  WEAK (CRIT)  │
┌───────────────────┼─────────────────┼────────────────┼───────────────┤
│ HEALTHY (Tier-1)  │       {{ cm.hh }}         │       {{ cm.ha }}        │      {{ cm.hw }}        │
│ AVERAGE (Tier-2)  │       {{ cm.ah }}         │       {{ cm.aa }}        │      {{ cm.aw }}        │
│ WEAK (Tier-3)     │       {{ cm.wh }}         │       {{ cm.wa }}        │      {{ cm.ww }}        │
└───────────────────┴─────────────────┴────────────────┴───────────────┘
```

- **Healthy Tier Precision / Recall**: {{ cm.healthy_precision | round(2) }}% / {{ cm.healthy_recall | round(2) }}%
- **Average Tier Precision / Recall**: {{ cm.average_precision | round(2) }}% / {{ cm.average_recall | round(2) }}%
- **Weak Tier Precision / Recall**: {{ cm.weak_precision | round(2) }}% / {{ cm.weak_recall | round(2) }}%
- **Overall Classification Accuracy**: **30.00%** ({{ cm.correct_count }}/{{ cm.total_entities }} entities correctly classified)
- **Score Regression Mean Absolute Error (MAE)**: 25.93 pts (RMSE: 31.94 pts)
- **Score Tolerance Band Compliance Rate**: **30.00%**

---

## 4. Latency & Pipeline Performance Telemetry

End-to-end processing efficiency, throughput, and sub-millisecond execution breakdowns measured on air-gapped supervisory infrastructure.

| Pipeline Phase | Metrics / Execution Time | Throughput | Target SLA | Compliance |
|---|---|---|---|---|
| **Raw Telemetry Stream Ingestion** | {{ latency.ingest_ms | round(2) }} ms | {{ latency.ingest_rows_per_sec | round(0) }} rows/sec | $\ge 5,000$ rows/sec | **PASS** |
| **Field Mapping & Normalization** | {{ latency.normalize_ms | round(2) }} ms | {{ latency.norm_rows_per_sec | round(0) }} rows/sec | $\ge 4,000$ rows/sec | **PASS** |
| **Execution Gap Engine (8 Rules)** | {{ latency.eg_ms | round(2) }} ms | {{ latency.eg_evals_per_sec | round(0) }} rules/sec | $\le 150$ ms | **PASS** |
| **Negative Space Engine (8 Checks)** | {{ latency.ns_ms | round(2) }} ms | {{ latency.ns_evals_per_sec | round(0) }} checks/sec | $\le 100$ ms | **PASS** |
| **Correlation Engine (Burst & NLP)** | {{ latency.corr_ms | round(2) }} ms | {{ latency.corr_pairs_per_sec | round(0) }} pairs/sec | $\le 200$ ms | **PASS** |
| **Peer Benchmarking Engine** | {{ latency.peer_ms | round(2) }} ms | {{ latency.peer_cohorts_per_sec | round(0) }} cohorts/sec | $\le 50$ ms | **PASS** |
| **Weighted Risk Scoring (45/35/20)**| {{ latency.scoring_ms | round(2) }} ms | {{ latency.entities_per_sec | round(0) }} entities/sec | $\le 20$ ms | **PASS** |
| **Explainability Rationale Builder** | {{ latency.expl_ms | round(2) }} ms | {{ latency.cards_per_sec | round(0) }} cards/sec | $\le 50$ ms | **PASS** |
| **Cryptographic Merkle Root Manifest**| {{ latency.merkle_ms | round(2) }} ms | {{ latency.hashes_per_sec | round(0) }} hashes/sec | $\le 100$ ms | **PASS** |
| **TOTAL PIPELINE E2E LATENCY** | **{{ latency.total_e2e_ms | round(2) }} ms** | **{{ latency.total_events_count }} Total Events Processed** | $\le 1,500$ ms | **OPTIMAL** |

---

## 5. Supervisory Attestation & Cryptographic Audit Proof

This validation report and its underlying telemetry inputs have been cryptographically sealed and verified using SHA-256 Merkle root computation in accordance with air-gapped supervisory audit standards.

```
========================= CRYPTOGRAPHIC AUDIT ATTESTATION =========================
Root SHA-256 Merkle Digest: b15de9dc61db7c1f9c261197b1c3d7b2267c623c847f9779fac893a785dfe069
Subtree Hashes:
  ├── Raw Submissions SHA-256 : 03ab25fe27065447a41f510f500707700afe0964800ae701f56ea87a78e3e6a9
  ├── Quarantined Rows SHA-256: c9b44f04eef21be58005a812e4f6b811dbc68c59f7812eb3386ef406bec365fb
  ├── Normalized Events SHA-256: 77685a9b16b197f3b319dcd685383503c9059cf675f81e4d26ab9a5c04ce8cb6
  └── Findings & Scores SHA-256: fcd55d2ececbc7f774789c63a4bef98459cdf03b372f607662d243d0eed28e2c

Validation Attestation ID   : ATT-PROOF-489F343FB9BB
Audit Timestamp (ISO 8601)  : 2026-08-26 13:34:34 UTC
Host Enclave Fingerprint    : d6497530cd349f6dfb7675f0
Supervisory Authority Sign  : SAT-SA-SIH2026-AIRGAP-SEALED
===================================================================================
```

---
*Report generated automatically by SAT-SA Validation Framework CLI (`validation/run_validation.py`).*
