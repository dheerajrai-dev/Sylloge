# Test & Verification Suite (`testing/`)

> **Master 234-Test Verification Suite** covering unit tests, service integration tests, adversarial stress modules, and end-to-end pipeline verification.

---

## 🎯 Purpose
- Maintains the comprehensive 234-test automated verification suite for the SAT-SA platform.
- Validates mathematical precision, schema integrity, and rule correctness across all analytics engines.
- Conducts adversarial stress testing against corrupted headers, metric gaming, and synthetic heartbeats.
- Verifies end-to-end integration flows from raw file ingestion down to risk scoring and Merkle sealing.

---

## 💎 Why This Subsystem Is Critical
- **Quality Assurance:** Guarantees that code refactoring does not introduce analytical regressions or silent detection failures.
- **Adversarial Resilience:** Tests system robustness against evasion techniques (such as synthetic periodic heartbeats or rapid batch closures).
- **Statutory Reliability:** Proves to evaluators and regulators that the platform's outputs are 100% reproducible and mathematically sound.

---

## 🧩 Main Components & Test Inventory

```text
testing/
├── conftest.py                      # Master Pytest fixtures (SQLite Async DB, mock tokens, entities)
├── test_full_pipeline_e2e.py        # End-to-end multi-service ingestion-to-scoring verification
├── test_backend_api.py              # FastAPI endpoint CRUD, auth & finding tests
├── test_analytics_engine.py         # 6-engine analytics verification tests
{{ ... }}
├── test_challenger_m3_stress.py     # 16-Rule individual adversarial stress validation
├── test_shared_models.py            # SQLAlchemy ORM model verification
├── test_shared_schemas.py           # Pydantic schema validation tests
├── test_shared_auth.py              # JWT token & Bcrypt hashing tests
└── test_shared_storage.py           # MinIO S3 object storage mock tests
```

---

## ⚙️ Key Responsibilities
- Execute unit and integration tests across all microservices.
- Verify 16 core rules (8 Execution Gap + 8 Negative Space) against seeded anomalies.
- Test quarantine error handling and data recovery mechanisms.
- Assert mathematical bounds on Shannon entropy, inter-arrival dispersion ($C_v$), and Z-scores.

---

## 🔄 Test Suite Verification Topology

```mermaid
flowchart TD
    subgraph FIXTURES["1. Test Environment Setup"]
        CONF["Pytest conftest.py<br/>• Async SQLite DB Session<br/>• Mock JWT Auth & Headers<br/>• Pre-Seeded Supervised Entities"]
    end

    subgraph TIERS["2. Test Execution Tiers (234 Total Tests)"]
        UNIT["<b>Unit & Service Tests</b><br/>• test_backend_api.py<br/>• test_analytics_engine.py<br/>• test_data_processing.py<br/>• test_audit_service.py"]
        ADV["<b>Adversarial Stress Modules</b><br/>• Module 1: Bad Timestamps<br/>• Module 2: Anti-Gaming Evasion<br/>• Module 3: Synthetic Heartbeats<br/>• Challenger M3 16-Rule Stress"]
        E2E["<b>End-to-End Pipeline Tests</b><br/>• test_full_pipeline_e2e.py<br/>Ingest ➔ Norm ➔ Analyze ➔ Score ➔ Seal"]
    end

    subgraph REPORT["3. Quality Assurance Verdict"]
        RES["<b>234 Passing Tests (100% Green)</b><br/>0 Regressions | 0 Failures | 0 Errors"]
    end

    CONF --> UNIT
    CONF --> ADV
    CONF --> E2E
    UNIT & ADV & E2E --> RES

    style FIXTURES fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    style TIERS fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#fff
    style REPORT fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#fff
```

---

## 📚 Related Master Documentation
- [**Doc 05: Operations & Developer Guide**](../docs/05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md) (Section 3: Testing & QA Framework)
