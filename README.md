# Sylloge

**Sylloge** is an offline, air-gapped supervisory cybersecurity analytics platform built for Smart India Hackathon (SIH 2026 Problem Statement 26157).

## Overview

Sylloge operates in strict air-gapped SOC enclaves with zero outbound internet connectivity. It ingests multi-vendor telemetry datasets across 8 dataset types, normalizes events into a canonical schema, evaluates entity risk using a 6-engine analytics core, and generates signed SHA-256 Merkle audit manifests.

## Key Features

- **Strict Air-Gapped Security**: Zero remote CDN calls, zero outbound telemetry.
- **Tripartite Weighted Risk Scoring**:
  - **Execution Gap Engine (45%)**: Detects SLA breaches, unassigned critical cases, and triage failures.
  - **Negative Space Engine (35%)**: EWMA volume cliff detection and Shannon entropy silence monitoring.
  - **Peer Benchmark Engine (20%)**: Sector baseline Z-score cohort comparison.
- **Cryptographic Audit Manifests**: Tamper-proof SHA-256 Merkle tree generation for supervisory compliance.
- **Interactive React SPA Dashboard**: Real-time entity rankings, worklists, findings, upload workflows, and printable PDF compliance dossiers.

## Quick Start

### 1. Environment Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 2. Launching Services via Docker Compose
```bash
docker compose up -d
```
Access points:
- **Frontend SPA Dashboard**: `http://localhost:3000`
- **Backend API Gateway**: `http://localhost:8000/docs`

### 3. Default Admin Access Credentials
- **Username**: `admin`
- **Password**: `supervisor_pass123` (configured via `ADMIN_PASSWORD` in `.env`)

### 4. Running Verification Tests
```bash
.\.venv\Scripts\pytest
```

## Demo Test Data (`sample-data/synthetic/`)

Pre-formatted CSV test datasets showcasing Execution Gap SLA breaches and Negative Space telemetry cliffs are available in the `sample-data/synthetic/` folder for SIH live judging demonstrations. See [sample-data/synthetic/](sample-data/synthetic/) for details.
