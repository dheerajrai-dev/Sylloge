"""Backend API Gateway router imports."""

from .auth import router as auth_router
from .benchmarks import router as benchmarks_router
from .dashboard import router as dashboard_router
from .entities import router as entities_router
from .findings import router as findings_router
from .health import router as health_router
from .pipeline import router as pipeline_router
from .reports import router as reports_router
from .submissions import router as submissions_router

__all__ = [
    "auth_router",
    "benchmarks_router",
    "dashboard_router",
    "entities_router",
    "findings_router",
    "health_router",
    "pipeline_router",
    "reports_router",
    "submissions_router",
]
