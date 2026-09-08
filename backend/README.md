# Backend API Gateway (`backend/`)

> **FastAPI REST API Gateway** orchestrating authentication, entity registries, findings explorer, supervisory reports, and microservice pipeline triggers.

---

## 🎯 Purpose
- Functions as the central API Gateway and orchestration controller for the entire SAT-SA platform.
- Exposes secure, asynchronous REST API endpoints consumed by the React frontend.
- Enforces local authentication, session security, and supervisor role-based access boundaries.
- Coordinates cross-service execution across data processing, analytics, and audit microservices.

---

## 💎 Why This Subsystem Is Critical
- **Platform Ingress Controller:** Central communication hub routing client traffic to storage and analytics services.
- **Security & Authorization:** Enforces air-gapped token validation and Bcrypt password hashing (`rounds=12`).
- **Decoupled Architecture:** Isolates web API presentation from computationally intensive statistical analytics.

---

## 🧩 Main Components & Directory Map

```text
backend/app/
├── main.py                  # FastAPI application entrypoint, CORS & router aggregation
├── config.py                # Environment configurations & microservice URLs
├── routers/                 # Domain-specific REST API endpoints
│   ├── auth.py              # Local Bcrypt JWT login (/api/v1/auth/login)
│   ├── entities.py          # Regulated entity CRUD, risk history & radar metrics
│   ├── submissions.py       # Multi-file telemetry upload & ingestion dispatching
│   ├── findings.py          # Unified findings query, evidence drill-down & notes
│   ├── dashboard.py         # Pre-aggregated worklists & national risk metrics
│   ├── benchmarks.py        # Sector peer cohort distributions & Z-scores
│   ├── pipeline.py          # Analytics pipeline execution triggers
│   ├── reports.py           # PDF compliance audit dossier exports
│   └── health.py            # Microservice liveness & readiness probes
└── services/                # Business logic handlers & inter-service HTTP clients
```

---

## ⚙️ Key Responsibilities
- Validate incoming API payloads using strict Pydantic schemas.
- Route telemetry upload streams to the ingestion service.
- Query and persist normalized records, findings, and risk scores in PostgreSQL.
- Aggregate multi-dimensional metrics for fast frontend rendering.

---

## 🔄 Ingress & Request Orchestration Flow

```mermaid
flowchart TD
    subgraph CLIENT["1. Client Layer"]
        SPA["React 18 SPA Dashboard<br/>Axios API Client (client.ts)"]
    end

    subgraph GATEWAY["2. FastAPI API Gateway (backend/app/)"]
        AUTH{"Auth & JWT Middleware<br/>Bearer Token Validation"}
        ROUTER["Domain Routers<br/>• /api/v1/dashboard<br/>• /api/v1/entities<br/>• /api/v1/findings<br/>• /api/v1/pipeline"]
        SVC["Service Layer & Handlers<br/>Async DB Sessions"]
    end

    subgraph PERSIST["3. Data Persistence"]
        DB[("PostgreSQL 16 DB<br/>Relational Data Store")]
        S3[("MinIO S3 Store<br/>Raw Files & Reports")]
    end

    subgraph SVCS["4. Internal Microservices"]
        DP["Data Processing Service (:8001)<br/>Ingestion & Normalization"]
        AE["Analytics Engine (:8002)<br/>6-Engine Analytics Pipeline"]
        AS["Audit Service (:8003)<br/>Merkle Root Attestation"]
    end

    SPA --> AUTH
    AUTH --> ROUTER
    ROUTER --> SVC
    SVC --> DB
    SVC --> S3
    SVC -.->|HTTP Dispatch| DP
    SVC -.->|Trigger Pipeline| AE
    SVC -.->|Generate Manifest| AS

    style CLIENT fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    style GATEWAY fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#fff
    style PERSIST fill:#0f172a,stroke:#06b6d4,stroke-width:2px,color:#fff
    style SVCS fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#fff
```

---

## 📚 Related Master Documentation
- [**Doc 02: System Architecture Guide**](../docs/02_SYSTEM_ARCHITECTURE.md) (Section 6: Backend API Gateway Architecture)
- [**Doc 03: Codebase & Tech Stack Guide**](../docs/03_CODEBASE_AND_TECH_STACK_GUIDE.md) (Section 3.1: Backend Microservice)
- [**Doc 05: Operations & Developer Guide**](../docs/05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md) (Section 1: Local Development)
