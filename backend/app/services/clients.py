"""Inter-Service REST API Clients for SAT-SA Microservice Topology."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional
import httpx

from shared.config import settings
from shared.logging import logger
from ..config import backend_settings


class BaseServiceClient:
    """Base client with authentication headers and timeout handling."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY,
            "Content-Type": "application/json",
        }

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.base_url}{path}"
            resp = await client.get(url, headers=self.headers, params=params)
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{self.base_url}{path}"
            resp = await client.post(url, headers=self.headers, json=json_data)
            resp.raise_for_status()
            return resp.json()


class DataProcessingClient(BaseServiceClient):
    """Client for Data Processing microservice (:8001)."""

    def __init__(self, base_url: Optional[str] = None):
        super().__init__(base_url or backend_settings.DATA_PROCESSING_URL)

    async def health(self) -> Dict[str, Any]:
        return await self.get("/health")

    async def ingest_submission(
        self,
        submission_id: uuid.UUID,
        dataset_type: str,
        entity_id: uuid.UUID,
        file_path: str,
    ) -> Dict[str, Any]:
        payload = {
            "submission_id": str(submission_id),
            "dataset_type": dataset_type,
            "entity_id": str(entity_id),
            "file_path": file_path,
        }
        return await self.post("/api/v1/ingest/", json_data=payload)

    async def normalize_submission(
        self,
        submission_id: uuid.UUID,
        profile_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        payload = {
            "submission_id": str(submission_id),
            "profile_id": str(profile_id) if profile_id else None,
        }
        return await self.post("/api/v1/normalize/submission", json_data=payload)

    async def get_quarantine_summary(self, submission_id: uuid.UUID) -> Dict[str, Any]:
        return await self.get(f"/api/v1/quarantine/submission/{submission_id}")


class AnalyticsEngineClient(BaseServiceClient):
    """Client for Analytics & Scoring microservice (:8002)."""

    def __init__(self, base_url: Optional[str] = None):
        super().__init__(base_url or backend_settings.ANALYTICS_ENGINE_URL)

    async def health(self) -> Dict[str, Any]:
        return await self.get("/health")

    async def analyze_entity(
        self,
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        sector: Optional[str] = None,
        size_tier: Optional[str] = None,
        persist_to_db: bool = True,
    ) -> Dict[str, Any]:
        payload = {
            "entity_id": str(entity_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "sector": sector,
            "size_tier": size_tier,
            "persist_to_db": persist_to_db,
        }
        return await self.post("/api/v1/analytics/analyze", json_data=payload)

    async def get_scores(self, entity_id: uuid.UUID, limit: int = 20) -> List[Dict[str, Any]]:
        return await self.get(f"/api/v1/analytics/scores/{entity_id}", params={"limit": limit})


class AuditServiceClient(BaseServiceClient):
    """Client for Cryptographic Audit microservice (:8003)."""

    def __init__(self, base_url: Optional[str] = None):
        super().__init__(base_url or backend_settings.AUDIT_SERVICE_URL)

    async def health(self) -> Dict[str, Any]:
        return await self.get("/health")

    async def generate_manifest(
        self,
        entity_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        manifest_type: str = "PERIODIC_AUDIT",
        submission_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        payload = {
            "entity_id": str(entity_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "manifest_type": manifest_type,
            "submission_id": str(submission_id) if submission_id else None,
        }
        return await self.post("/api/v1/audit/manifest", json_data=payload)

    async def verify_manifest(self, manifest_id: uuid.UUID) -> Dict[str, Any]:
        payload = {"manifest_id": str(manifest_id)}
        return await self.post("/api/v1/audit/verify", json_data=payload)

    async def get_latest_manifest(self, entity_id: uuid.UUID) -> Dict[str, Any]:
        return await self.get(f"/api/v1/audit/manifest/entity/{entity_id}/latest")
