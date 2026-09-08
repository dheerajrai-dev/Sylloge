# Infrastructure & Deployment (`infrastructure/`)

> **Container & Deployment Configurations** orchestrating Docker Compose multi-service stacks, Nginx reverse proxy routing, and PostgreSQL initialization scripts.

---

## 🎯 Purpose
- Houses all infrastructure-as-code, container definitions, and reverse proxy routing configurations.
- Enables one-click deployment of the entire 5-microservice platform inside air-gapped environments.
- Defines production Nginx reverse proxy routing and SSL termination.
- Manages relational database bootstrap scripts and extension configurations.

---

## 💎 Why This Subsystem Is Critical
- **Air-Gap Provisioning:** Ensures the platform can be cleanly deployed on an isolated host without internet connectivity.
- **Service Orchestration:** Defines networking, container startup dependencies, health checks, and volume mounts.
- **Routing & Isolation:** Routes client web requests cleanly to frontend and backend services via a single unified ingress port.

---

## 🧩 Main Components & Directory Map

```text
infrastructure/
├── nginx/
│   ├── nginx.conf           # Production Nginx reverse proxy configuration & routing
│   └── Dockerfile           # Nginx container definition
├── postgres/
│   └── init.sql             # Initial database bootstrap & extension creation
└── docker-compose.yml       # Master 5-service local deployment stack (in root)
```

---

## ⚙️ Key Responsibilities
- Define multi-container runtime environment and port mappings.
- Provide persistent local storage volumes for PostgreSQL and MinIO S3 data.
- Manage service health checks and restart policies.
- Ensure zero-internet isolation across container networks.

---

## 🔄 Air-Gapped Container Ingress Topology

```mermaid
flowchart TD
    subgraph INGRESS["1. Network Ingress Gate"]
        CLIENT["Supervisor Browser<br/>(Air-Gapped Workstation)"]
        NGINX["Nginx Reverse Proxy (:80 / :3000)<br/>infrastructure/nginx/nginx.conf"]
    end

    subgraph APP_CONTAINERS["2. Application Services"]
        FE["Frontend SPA Container<br/>(Node 18 Alpine / Static)"]
        BE["Backend API Gateway (:8000)<br/>(Python 3.11 FastAPI)"]
    end

    subgraph ENGINE_CONTAINERS["3. Microservice Workers"]
        DP["Data Processing (:8001)<br/>(Ingestion & Normalizer)"]
        AE["Analytics Engine (:8002)<br/>(6 Supervisory Engines)"]
        AS["Audit Service (:8003)<br/>(SHA-256 Merkle Engine)"]
    end

    subgraph STORAGE_TIER["4. Persistent Air-Gapped Storage"]
        PG[("PostgreSQL 16 DB<br/>sat_sa Database")]
        MINIO[("MinIO S3 Store<br/>Local Object Buckets")]
    end

    CLIENT --> NGINX
    NGINX -->|Static UI Assets| FE
    NGINX -->|/api/* Requests| BE

    BE <--> DP
    BE <--> AE
    BE <--> AS

    DP & AE & AS & BE <--> PG
    DP & BE <--> MINIO

    style INGRESS fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#fff
    style APP_CONTAINERS fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#fff
    style ENGINE_CONTAINERS fill:#0f172a,stroke:#06b6d4,stroke-width:2px,color:#fff
    style STORAGE_TIER fill:#1e293b,stroke:#10b981,stroke-width:2px,color:#fff
```

---

## 📚 Related Master Documentation
- [**Doc 02: System Architecture Guide**](../docs/02_SYSTEM_ARCHITECTURE.md) (Section 15: Physical Air-Gap Deployment Architecture)
- [**Doc 05: Operations & Developer Guide**](../docs/05_OPERATIONS_DEPLOYMENT_AND_DEVELOPER_GUIDE.md) (Section 2: Air-Gapped Deployment & Docker)

