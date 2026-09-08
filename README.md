# Sylloge (SAT-SA)

> **Offline, Air-Gapped Supervisory Cybersecurity Analytics Platform**  
> Built for **Smart India Hackathon (SIH 2026 Problem Statement 26157)**.

---

## 🛡️ Executive Overview

**Sylloge** is an enterprise-grade supervisory cybersecurity analytics platform engineered for strict, air-gapped Security Operations Center (SOC) enclaves operating without outbound internet access or third-party cloud dependencies. 

The platform ingests multi-vendor security telemetry across 8 core log types, normalizes events into a unified canonical schema, evaluates institutional entity risk using a 6-engine analytics core, generates signed SHA-256 Merkle audit manifests, and renders supervisory compliance audit dossiers.

---

## 🎯 Primary Use Cases

- **Supervisory SOC Oversight**: Evaluates institutional SOC operational diligence, highlighting SLA breaches, unassigned critical incidents, and triage rubber-stamping.
- **Telemetry Absence & Silence Detection**: Monitors volume cliffs, missing off-hours analyst activity, and categorical Shannon entropy anomalies to identify sensor silences or intentional evasion.
- **Sector Peer Benchmarking**: Computes cohort Z-score baselines across regulated entities to pinpoint operational risk outliers requiring supervisory audit.
- **Cryptographic Tamper-Proof Compliance**: Constructs SHA-256 Merkle trees over ingested datasets and finding records to guarantee audit integrity.

---

## ⚡ Core Features & 6-Engine Analytics Engine

- **Air-Gapped Compliance**: Zero external CDN calls, offline bundled static assets, and air-gapped enclave compatibility.
- **Tripartite Analytics Engine Core**:
  - **Execution Gap Engine (45% Weight)**: Detects SLA breaches (critical alert 2h SLA, P1 escalation > 4h), stale cases (>72h idle), unassigned critical assets, and rapid batch closures.
  - **Negative Space Engine (35% Weight)**: EWMA volume cliff detection, missing weekend/off-hours analyst activity, crown-jewel asset uptime drops, and low Shannon entropy.
  - **Peer Benchmark Engine (20% Weight)**: Cohort Z-score comparison against sector baselines.
  - **Correlation Engine**: Multi-alert burst clustering, TF-IDF note clone detection, and asset grouping.
  - **Risk Scoring Engine**: Deterministic aggregation into Healthy, Average, and Weak entity risk tiers.
  - **Explainability Engine**: Natural language narrative summaries explaining root-cause risk drivers.
- **Interactive SPA Dashboard**: Real-time entity rankings, worklists, findings detail views, and printable PDF compliance dossiers.

---

## 🏗️ System Architecture

```text
├── analytics_engine/    # 6 Analytics Engines (Execution Gap, Negative Space, etc.)
├── backend/             # FastAPI REST API Gateway, SQLAlchemy ORM & Auth
├── frontend/            # React SPA Dashboard (Vite, TailwindCSS, Recharts)
├── data_processing/     # Field Mapping & Canonical Schema Normalization
├── audit_service/       # Cryptographic Merkle Root Verification Engine
├── shared/              # Shared data models, schemas, auth & storage
├── testing/             # Unit, integration & adversarial test suites
├── validation/          # Automated Precision/Recall Validation CLI & Compliance Reporting
└── docs/                # Comprehensive 5-Document Master Engineering System

---

## 📚 Master Engineering Documentation System

The repository is fully documented across 5 authoritative guides in `docs/`:

1. [**01_PRODUCT_AND_BUSINESS_GUIDE.md**](file:///docs/01_PRODUCT_AND_BUSINESS_GUIDE.md): Executive summary, NCIIPC mandate (Section 70A IT Act), personas, 6 supervisory views, lifecycles, and 90s hero demo.
2. [**02_SYSTEM_ARCHITECTURE.md**](file:///docs/02_SYSTEM_ARCHITECTURE.md): 9-layer physical pipeline, 11-layer logical architecture, 5 microservices, PostgreSQL ERD, MinIO S3, and sequence flows.
3. [**03_CODEBASE_AND_TECH_STACK_GUIDE.md**](file:///docs/03_CODEBASE_AND_TECH_STACK_GUIDE.md): Tech stack rationale, folder-by-folder codebase breakdown, file inventory, dependency maps, and upload-to-sealing trace.
4. [**04_ANALYTICS_AND_DATA_ENGINE.md**](file:///docs/04_ANALYTICS_AND_DATA_ENGINE.md): Mathematical formulas (EWMA 3-sigma, Shannon entropy, CV dispersion), 8 EG rules + 8 NS checks + catalogs, Z-scores, and Tripartite Risk.
5. [**05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md**](file:///docs/05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md): Local startup runbooks, air-gapped Docker Compose deployment, testing, extension tutorials, and troubleshooting runbooks.
- [**DOCS_AUDIT_REPORT.md**](file:///docs/DOCS_AUDIT_REPORT.md): Audit log of reviewed artifacts, resolved discrepancies, and migration log.
```

---

## 🛠️ Setup & Installation Guide

### Prerequisites
- **Docker & Docker Compose** (Recommended for containerized deployment)
- **Python 3.11+** (For local backend development & testing)
- **Node.js 18+ & npm** (For local frontend development)

---

### Method A: Containerized Deployment (Recommended)

1. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```

2. **Launch Services with Docker Compose**:
   ```bash
   docker compose up -d --build
   ```

3. **Verify Deployment**:
   - **Frontend SPA Dashboard**: `http://localhost:3000`
   - **Backend API Documentation**: `http://localhost:8000/docs`

---

### Method B: Manual Local Development Setup

#### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Validation Guide

### 1. Automated Supervisory Validation CLI
Run the validation suite to evaluate engine detection precision, recall, F1 scores, and confusion matrix accuracy:

```bash
python validation/run_validation.py
```

Validation CLI Options:
- `--min-f1`: Minimum F1 score compliance threshold (Default: `0.90`)
- `--min-tier-acc`: Minimum tier accuracy threshold (Default: `0.90`)
- `--output-report`: Target path for generated markdown audit report (Default: `validation/VALIDATION_REPORT.md`)

---

### 2. Unit & Integration Test Suite
Execute backend unit tests with pytest:

```bash
pytest
```

To run tests with coverage reporting:
```bash
pytest --cov=backend --cov=analytics_engine
```


