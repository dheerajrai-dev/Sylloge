"""FastAPI Application Entrypoint for SAT-SA Analytics Engine Microservice (Port 8002)."""

import contextlib
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.errors import SATSAError
from shared.logging import logger
from .config import analytics_settings
from .routers import (
    analytics_router,
    benchmarks_router,
    health_router,
    rules_router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(
        f"Starting {analytics_settings.SERVICE_NAME} v{analytics_settings.SERVICE_VERSION} "
        f"on {analytics_settings.HOST}:{analytics_settings.PORT}"
    )
    yield
    logger.info(f"Shutting down {analytics_settings.SERVICE_NAME}")


app = FastAPI(
    title="Sylloge Analytics & Scoring Engine",
    description="Offline air-gapped supervisory analytics, multi-engine risk scoring, and explainability service.",
    version=analytics_settings.SERVICE_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(SATSAError)
async def custom_satsa_error_handler(request: Request, exc: SATSAError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include Routers
app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(rules_router)
app.include_router(benchmarks_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=analytics_settings.HOST,
        port=analytics_settings.PORT,
        reload=settings.DEBUG,
    )
