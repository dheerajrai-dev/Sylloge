"""Routers package for analytics-engine."""

from .analytics import router as analytics_router
from .benchmarks import router as benchmarks_router
from .health import router as health_router
from .rules import router as rules_router

__all__ = [
    "health_router",
    "analytics_router",
    "rules_router",
    "benchmarks_router",
]
