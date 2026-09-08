# SAT-SA — Operations, Deployment & Developer Guide

> **Document ID:** `05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md`  
> **Classification:** Unclassified / Technical Operations & Developer Manual  
> **System Name:** SAT-SA (Sylloge Supervisory Analytics)  
> **Target Problem Statement:** PS-26157 (NCIIPC / National Critical Information Infrastructure Protection Centre)  
> **Target Audience:** DevOps Engineers, Site Reliability Engineers (SREs), Full-Stack Developers, QA Engineers, and Enclave Administrators.  
> **Document Purpose:** Complete, step-by-step operational manual for local setup, air-gapped container deployment, test suite execution, disaster recovery, data ingestion operations, platform extension tutorials, and troubleshooting runbooks.

---

## Table of Contents

1. [Local Development Environment Setup](#1-local-development-environment-setup)
    - 1.1 [Prerequisites & Toolchain](#11-prerequisites--toolchain)
    - 1.2 [Environment Configuration (`.env.example` vs `.env`)](#12-environment-configuration-envexample-vs-env)
    - 1.3 [Python Virtual Environment & Dependency Installation](#13-python-virtual-environment--dependency-installation)
    - 1.4 [Database Initialization & Alembic Migrations](#14-database-initialization--alembic-migrations)
    - 1.5 [Starting the 5 Microservices Locally](#15-starting-the-5-microservices-locally)
2. [Production & Air-Gapped Enclave Deployment](#2-production--air-gapped-enclave-deployment)
    - 2.1 [One-Click Docker Compose Stack](#21-one-click-docker-compose-stack)
    - 2.2 [Air-Gap Physical Media Provisioning Workflow](#22-air-gap-physical-media-provisioning-workflow)
    - 2.3 [Production Nginx Reverse Proxy Configuration](#23-production-nginx-reverse-proxy-configuration)
    - 2.4 [Zero-Internet Air-Gap Integrity Verification](#24-zero-internet-air-gap-integrity-verification)
3. [Testing, Validation & Quality Assurance Framework](#3-testing-validation--quality-assurance-framework)
    - 3.1 [Pytest Test Suite Execution Commands](#31-pytest-test-suite-execution-commands)
    - 3.2 [Frontend TypeScript Typecheck & Production Build](#32-frontend-typescript-typecheck--production-build)
    - 3.3 [Automated Validation Suite Runner (`run_validation.py`)](#33-automated-validation-suite-runner-run_validationpy)
4. [Operations, Monitoring & Disaster Recovery](#4-operations-monitoring--disaster-recovery)
    - 4.1 [Microservice Health Checks & Endpoints](#41-microservice-health-checks--endpoints)
    - 4.2 [Structured JSON Logging](#42-structured-json-logging)
    - 4.3 [PostgreSQL Backup & Restore Strategy](#43-postgresql-backup--restore-strategy)
    - 4.4 [MinIO S3 Immutable Storage Retention](#44-minio-s3-immutable-storage-retention)
    - 4.5 [Enclave Cold-Start Recovery Procedure](#45-enclave-cold-start-recovery-procedure)
5. [Data Ingestion & Quarantine Operations](#5-data-ingestion--quarantine-operations)
    - 5.1 [Supported Telemetry File Formats](#51-supported-telemetry-file-formats)
    - 5.2 [Batch Upload via UI Wizard & REST API](#52-batch-upload-via-ui-wizard--rest-api)
    - 5.3 [Quarantine Queue Inspection & Triage](#53-quarantine-queue-inspection--triage)
6. [Extending the Platform (Step-by-Step Developer Tutorials)](#6-extending-the-platform-step-by-step-developer-tutorials)
    - 6.1 [How to Add a New Execution Gap Rule](#61-how-to-add-a-new-execution-gap-rule)
    - 6.2 [How to Add a New Negative Space Check](#62-how-to-add-a-new-negative-space-check)
    - 6.3 [How to Add a New Canonical Telemetry Dataset](#63-how-to-add-a-new-canonical-telemetry-dataset)
    - 6.4 [How to Add a New Dashboard View or Chart Component](#64-how-to-add-a-new-dashboard-view-or-chart-component)
    - 6.5 [How to Tune Risk Scoring Weights & Cohort Baselines](#65-how-to-tune-risk-scoring-weights--cohort-baselines)
7. [Contributing & Engineering Standards](#7-contributing--engineering-standards)
8. [Comprehensive Troubleshooting Guide & Runbook](#8-comprehensive-troubleshooting-guide--runbook)

---

## 1. Local Development Environment Setup

### 1.1 Prerequisites & Toolchain
Ensure the following base tools are installed on the local developer workstation:
- **Operating System:** Linux (Ubuntu 22.04+), macOS (ARM64/x86), or Windows 11 (PowerShell / WSL2).
- **Python:** Version `3.11` to `3.14`.
- **Node.js & npm:** Node.js `v18.0.0+` (LTS recommended) and npm `v9.0.0+`.
- **Docker & Docker Compose:** Docker Desktop `v26.0+` and Docker Compose `v2.24+`.
- **PostgreSQL Client (Optional):** `psql` for local database inspection.

---

### 1.2 Environment Configuration (`.env.example` vs `.env`)

Create a local `.env` file at the root of the project by copying `.env.example`:

```powershell
# In PowerShell (Windows)
Copy-Item .env.example .env

# In Bash (Linux / macOS)
cp .env.example .env
```

#### Master Configuration Reference Table

```
+---------------------------+-------------------------------------------------------+---------------------------------------+
| Environment Variable Name | Default Local Value                                   | Purpose & Description                 |
+---------------------------+-------------------------------------------------------+---------------------------------------+
| `ENVIRONMENT`             | `development`                                         | Application runtime mode              |
| `DEBUG`                   | `true`                                                | Enables verbose logging & debug modes |
| `DATABASE_URL`            | `postgresql+asyncpg://postgres:postgres@localhost:5432/satsa` | Async SQLAlchemy PostgreSQL URL       |
| `SYNC_DATABASE_URL`       | `postgresql://postgres:postgres@localhost:5432/satsa` | Sync SQLAlchemy DB URL (for tests)    |
| `MINIO_ENDPOINT`          | `localhost:9000`                                      | MinIO S3 API host and port            |
| `MINIO_ACCESS_KEY`        | `minioadmin`                                          | MinIO root access key                 |
| `MINIO_SECRET_KEY`        | `minioadmin`                                          | MinIO root secret key                 |
| `MINIO_SECURE`            | `false`                                               | Use TLS/HTTPS for local S3 calls      |
| `JWT_SECRET_KEY`          | `super_secret_airgap_jwt_key_2026_sih`                | Secret for signing local JWT tokens   |
| `INTERNAL_SERVICE_KEY`    | `test_internal_service_key_2026`                      | Inter-service auth header validation  |
| `DATA_PROCESSING_URL`     | `http://localhost:8001`                               | Data Processing service endpoint      |
| `ANALYTICS_ENGINE_URL`    | `http://localhost:8002`                               | Analytics Engine service endpoint     |
| `AUDIT_SERVICE_URL`       | `http://localhost:8003`                               | Audit Manifest service endpoint       |
| `BACKEND_URL`             | `http://localhost:8000`                               | Backend API Gateway service endpoint  |
| `CORS_ORIGINS`            | `["http://localhost:3000","http://localhost:80"]`     | Allowed client origins for CORS       |
+---------------------------+-------------------------------------------------------+---------------------------------------+
```

---

### 1.3 Python Virtual Environment & Dependency Installation

```powershell
# 1. Create Python Virtual Environment
python -m venv .venv

# 2. Activate Virtual Environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS Bash:
source .venv/bin/activate

# 3. Upgrade Pip & Install Dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 1.4 Database Initialization & Alembic Migrations

If running against a local PostgreSQL instance (or via Docker Compose), run the schema migrations:

```powershell
# 1. Run Alembic Migrations to head
alembic upgrade head

# 2. (Optional) Verify Schema in psql
# Tables created: entities, submission_batches, normalized_events,
# quarantine_records, execution_gap_findings, negative_space_findings,
# correlations, peer_benchmarks, risk_scores, audit_manifests, users.
```

---

### 1.5 Starting the 5 Microservices Locally

For active development, run each service in a separate terminal:

```powershell
# Terminal 1: Backend API Gateway (Port 8000)
$env:PYTHONPATH="."
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Data Processing Service (Port 8001)
$env:PYTHONPATH="."
.\.venv\Scripts\python -m uvicorn data_processing.app.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3: Analytics Engine Service (Port 8002)
$env:PYTHONPATH="."
.\.venv\Scripts\python -m uvicorn analytics_engine.app.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 4: Audit Service (Port 8003)
$env:PYTHONPATH="."
.\.venv\Scripts\python -m uvicorn audit_service.app.main:app --host 0.0.0.0 --port 8003 --reload

# Terminal 5: Frontend React Client (Port 3000)
cd frontend
npm install
npm run dev
```

The application will be accessible at `http://localhost:3000`.

---

## 2. Production & Air-Gapped Enclave Deployment

### 2.1 One-Click Docker Compose Stack

In an air-gapped production environment, start the entire containerized infrastructure with a single command:

```powershell
docker compose up -d --build
```

#### Service Health & Port Mapping
- `frontend`: `http://<ENCLAVE_HOST>:3000` (or `http://<ENCLAVE_HOST>:80` via Nginx)
- `backend`: `http://<ENCLAVE_HOST>:8000/docs` (Swagger UI)
- `data_processing`: `http://<ENCLAVE_HOST>:8001/docs`
- `analytics_engine`: `http://<ENCLAVE_HOST>:8002/docs`
- `audit_service`: `http://<ENCLAVE_HOST>:8003/docs`
- `minio`: `http://<ENCLAVE_HOST>:9001` (MinIO Web Console)

To view real-time aggregated logs:
```powershell
docker compose logs -f
```

---

### 2.2 Air-Gap Physical Media Provisioning Workflow

```mermaid
sequenceDiagram
    participant CSE as Supervised CSE SOC
    participant USB as Encrypted Physical Media (USB/SSD)
    participant SEC_GATE as Enclave Air-Gap Media Scanner
    participant HOST as SAT-SA Production Host

    CSE->>USB: Export quarterly SOC telemetry CSV/JSON bundles
    CSE->>SEC_GATE: Physical handoff of encrypted USB
    SEC_GATE->>SEC_GATE: Run offline antivirus/malware signature scan
    SEC_GATE->>HOST: Mount read-only USB volume inside Enclave LAN
    HOST->>HOST: Ingest via SAT-SA Web UI (/upload) or CLI batch loader
```

---

### 2.3 Production Nginx Reverse Proxy Configuration

The reverse proxy configuration lives at `infrastructure/nginx/nginx.conf`:

```nginx
events { worker_connections 1024; }

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    client_max_body_size 500M;

    upstream backend_api {
        server backend:8000;
    }

    server {
        listen 80;
        server_name localhost;

        location /api/ {
            proxy_pass http://backend_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

---

### 2.4 Zero-Internet Air-Gap Integrity Verification

To verify that the deployment maintains complete air-gap compliance with zero external data leaks, run this test from within the host container:

```powershell
# Attempt external DNS lookup / ping from within containers
docker compose exec backend python -c "
import socket
try:
    socket.gethostbyname('google.com')
    print('FAIL: Outbound DNS resolved!')
except Exception:
    print('PASS: Verified Zero-Internet Air-Gapped Isolation.')
"
```

---

## 3. Testing, Validation & Quality Assurance Framework

### 3.1 Pytest Test Suite Execution Commands

SAT-SA contains comprehensive unit, integration, and adversarial stress suites.

#### 1. Core Service & Unit Tests
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest testing/test_analytics_engine.py testing/test_audit_service.py testing/test_shared_models.py testing/test_shared_schemas.py testing/test_shared_storage.py -v
```

#### 2. Adversarial & Boundary Stress Test Suites
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest testing/test_adversarial_m1.py testing/test_adversarial_m3.py testing/test_challenger_m3_stress.py -v
```

#### 3. Full End-to-End Pipeline Verification
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python -m pytest testing/test_full_pipeline_e2e.py -v
```

---

### 3.2 Frontend TypeScript Typecheck & Production Build

```powershell
cd frontend

# 1. Typecheck (Zero Errors Allowed)
npx tsc --noEmit

# 2. Production Static Bundle Build
npm run build
```

---

### 3.3 Automated Validation Suite Runner (`run_validation.py`)

To execute the automated validation suite against synthetic datasets with planted ground-truth anomalies:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python validation/run_validation.py --dataset-dir validation/synthetic_data --output validation/VALIDATION_REPORT.md
```

This verifies that precision, recall, and Macro F1-score across all 16 detection rules exceed the 95% threshold.

---

## 4. Operations, Monitoring & Disaster Recovery

### 4.1 Microservice Health Checks & Endpoints

Every microservice exposes standardized `/health` and `/readiness` endpoints:

```
+----+-------------------+-----------------------------------+-----------------------------------+
| #  | Microservice      | Health Endpoint                   | Expected Status Payload           |
+----+-------------------+-----------------------------------+-----------------------------------+
| 01 | `backend`         | `GET http://localhost:8000/health`| `{"status":"ok","service":"backend"}` |
| 02 | `data_processing` | `GET http://localhost:8001/health`| `{"status":"ok","service":"data_processing"}` |
| 03 | `analytics_engine`| `GET http://localhost:8002/health`| `{"status":"ok","service":"analytics_engine"}` |
| 04 | `audit_service`   | `GET http://localhost:8003/health`| `{"status":"ok","service":"audit_service"}` |
+----+-------------------+-----------------------------------+-----------------------------------+
```

---

### 4.2 Structured JSON Logging

Logs are formatted as structured JSON to enable easy indexing without external log forwarders (`shared/logging.py`):

```json
{
  "timestamp": "2026-09-08T17:15:00.123456+00:00",
  "service": "sat-sa-analytics",
  "level": "INFO",
  "logger": "sat-sa",
  "message": "Negative Space Engine evaluated 4 findings for entity 8f4a1234-5678-90ab-cdef-1234567890ab",
  "module": "engine",
  "line": 72
}
```

---

### 4.3 PostgreSQL Backup & Restore Strategy

```powershell
# 1. Automated PostgreSQL Database Dump
docker exec -t satsa_postgres pg_dump -U postgres -d satsa -F c -b -v -f /var/lib/postgresql/data/backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').dump

# 2. Database Restore from Dump
docker exec -i satsa_postgres pg_restore -U postgres -d satsa -v /var/lib/postgresql/data/backup_target.dump
```

---

### 4.4 MinIO S3 Immutable Storage Retention

MinIO data volumes are mapped to local host directory `./infrastructure/minio_data`. In production enclaves, this volume must be hosted on RAID-10 / WORM (Write-Once-Read-Many) storage arrays with daily volume snapshots.

---

### 4.5 Enclave Cold-Start Recovery Procedure

If the host hardware experiences an ungraceful shutdown:
1. Ensure Docker daemon is restarted: `sudo systemctl restart docker`.
2. Execute `docker compose up -d`.
3. Check container status: `docker compose ps`.
4. The Backend lifespan manager will automatically run `init_db_schema()` and re-establish DB connection pools.
5. The `audit_service` will verify stored SHA-256 Merkle root manifests against PostgreSQL state to confirm zero storage corruption during the power outage.

---

## 5. Data Ingestion & Quarantine Operations

### 5.1 Supported Telemetry File Formats
- **Standard Delimited Files:** `.csv`, `.tsv`, `.txt` (Auto-detects `,`, `;`, `\t`, `|`).
- **Structured JSON:** `.json` (Supports JSON arrays of objects and newline-delimited NDJSON streams).

---

### 5.2 Batch Upload via UI Wizard & REST API

#### Via UI Ingestion Wizard:
1. Navigate to `/upload`.
2. Select target Supervised CSE (e.g., `GreenGrid Power Ltd`).
3. Drag and drop telemetry files into the dropzone.
4. Auto-detection assigns schemas (01 to 08) with confidence scores.
5. Click **"Run Ingestion & Analytics Pipeline"**.
6. Review the live 9-Layer progress trace and view the Step 5 post-ingestion summary.

#### Via Backend REST API (`cURL` / PowerShell):
```powershell
$headers = @{ "Authorization" = "Bearer <SUPERVISOR_JWT_TOKEN>" }
$form = @{
    entity_id = "8f4a1234-5678-90ab-cdef-1234567890ab"
    period_start = "2026-07-01T00:00:00Z"
    period_end = "2026-09-30T23:59:59Z"
    files = Get-Item "C:\telemetry\01_alert_metadata.csv"
}
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/submissions" -Method Post -Headers $headers -Form $form
```

---

### 5.3 Quarantine Queue Inspection & Triage

When malformed rows are quarantined:
- Regulators can inspect quarantined lines via `GET /api/v1/quarantine?entity_id=<UUID>`.
- The quarantine log details: `raw_row_index`, `error_code`, `error_message`, and raw original row text.
- If quarantine rate exceeds 5% of submitted volume, the `DataTrustScore` indicator drops, alerting supervisors to potential data tampering.

---

## 6. Extending the Platform (Step-by-Step Developer Tutorials)

### 6.1 How to Add a New Execution Gap Rule

1. **Define the Rule in `analytics_engine/app/engines/execution_gap/default_rules.py`:**
   ```python
   RuleDefinition(
       rule_code="EG-31",
       name="Custom Escalation Tier Bypass",
       category="ESCALATION_BYPASS",
       target_dataset="case_management",
       filter_condition=RuleCondition(
           field="priority",
           operator=ConditionOperator.EQ,
           value="P1",
       ),
       temporal_join=TemporalJoin(
           target_dataset="escalation_records",
           join_key="case_id",
           relation=JoinRelation.NOT_EXISTS,
           max_time_delta_seconds=3600,  # 1 hour
       ),
       severity_base=90,
       confidence=0.95,
       description_template="P1 Case {case_id} unescalated after 1 hour.",
       rationale_template="Case {case_id} breached the 1-hour priority escalation SLA.",
       recommendation="Enforce automatic Tier-2 escalation routing.",
   )
   ```
2. **Add Unit Test in `analytics_engine/tests/test_execution_gap.py`:** Create a test with fixture events asserting rule `EG-31` fires.

---

### 6.2 How to Add a New Negative Space Check

1. **Define Check in `analytics_engine/app/engines/negative_space/default_checks.py`:**
   ```python
   CheckDefinition(
       check_id="NS-31",
       name="Zero Cloud Audit Logs",
       category="CLOUD_BLINDNESS",
       severity_base=80,
       confidence=0.90,
       min_sample_size=10,
       description_template="Cloud infrastructure claimed active but 0 audit logs detected.",
       rationale_template="Entity profile indicates AWS/Azure cloud presence, but 0 cloud audit events were submitted.",
       recommendation="Deploy CloudTrail/Activity Log telemetry forwarders.",
   )
   ```
2. **Implement Evaluation Logic in `analytics_engine/app/engines/negative_space/engine.py`:** Add `_eval_ns_31()` method checking cloud asset presence vs event counts.

---

### 6.3 How to Add a New Canonical Telemetry Dataset

1. **Add Enum Value:** In `shared/events/enums.py`, add `DatasetType.NEW_DATASET = "new_dataset"`.
2. **Create Parser:** Add `data_processing/app/parsers/new_dataset_parser.py` inheriting from `BaseParser`.
3. **Register Defaults:** Add alias mappings in `data_processing/app/mapping/defaults.py`.
4. **Update Frontend Detector:** Add column discriminators in `frontend/src/utils/datasetDetector.ts`.

---

### 6.4 How to Add a New Dashboard View or Chart Component

1. Create React component in `frontend/src/components/charts/NewChart.tsx`.
2. Create page component in `frontend/src/pages/NewViewPage.tsx`.
3. Register route in `frontend/src/App.tsx`.
4. Add navigation link in `frontend/src/components/layout/Sidebar.tsx`.

---

### 6.5 How to Tune Risk Scoring Weights & Cohort Baselines

- **Tuning Weights:** Pass custom weights to `RiskScoringEngine(weight_eg=0.40, weight_ns=0.40, weight_peer=0.20)`. Ensure $\sum W = 1.0$.
- **Updating Industry Baselines:** Modify `INDUSTRY_BASELINES` dictionary in `analytics_engine/app/engines/peer_benchmark/cohort.py`.

---

## 7. Contributing & Engineering Standards

- **Code Style:** Python code formatted via `black` and `ruff`; TypeScript code formatted via `prettier` and `eslint`.
- **Type Annotations:** 100% type hint coverage required on all Python functions and TypeScript interfaces.
- **Fail-Closed Principle:** Never swallow exceptions silently in data processing or audit services. Always log structured error details.
- **Zero Hallucination:** Never introduce external LLM calls or probabilistic deep learning models into the scoring path.

---

## 8. Comprehensive Troubleshooting Guide & Runbook

```
+------------------------------------+-----------------------------------+-----------------------------------------------+
| Observed Failure / Error Message   | Root Cause Analysis               | Step-by-Step Resolution Runbook               |
+------------------------------------+-----------------------------------+-----------------------------------------------+
| `HTTP 403: Invalid or missing      | Inter-service call missing the    | Ensure `X-Internal-Service-Key` header matches|
| internal service key`              | `INTERNAL_SERVICE_KEY` secret     | the `.env` value across all services.         |
|                                    |                                   |                                               |
| `ModuleNotFoundError: No module    | Python execution path is missing  | Set `$env:PYTHONPATH="."` (PowerShell) or     |
| named 'shared'`                    | root project directory            | `export PYTHONPATH="."` (Linux/Bash).         |
|                                    |                                   |                                               |
| `Merkle Root Hash Mismatch Alarm`  | Raw submission file in MinIO or   | Inspect Audit Trail log to identify which leaf|
|                                    | record in PostgreSQL was modified | was altered. Restore from backup if needed.   |
|                                    | post-ingestion                    |                                               |
|                                    |                                   |                                               |
| `Database Connection Timeout /     | PostgreSQL container not running  | Run `docker compose up -d postgres` and check |
| asyncpg.CannotConnectNowError`     | or connection pool exhausted      | `alembic upgrade head` migration status.      |
|                                    |                                   |                                               |
| `CORS Error in Browser Console`    | Frontend origin not in whitelist  | Add frontend IP/host to `CORS_ORIGINS` in     |
|                                    |                                   | root `.env` file and restart Backend service. |
|                                    |                                   |                                               |
| `Dataset Auto-Detection Failed`    | Non-standard CSV header delimiter | Check delimiter in first 2KB snippet; add     |
|                                    | or unrecognizable column aliases  | custom header alias to `datasetDetector.ts`.  |
+------------------------------------+-----------------------------------+-----------------------------------------------+
```

---
*End of Document 05 — Operations, Deployment & Developer Guide. You are now equipped with the complete engineering documentation for SAT-SA.*
