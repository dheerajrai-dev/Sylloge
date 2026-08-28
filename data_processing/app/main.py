"""FastAPI Application Entrypoint for SAT-SA Data Processing Microservice (Port 8001)."""

import contextlib
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.errors import SATSAError, StorageError, ValidationError
from shared.logging import logger
from .config import dp_settings
from .routers import (
    health_router,
    ingest_router,
    mapping_router,
    normalize_router,
    quarantine_router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(
        f"Starting {dp_settings.SERVICE_NAME} v{dp_settings.SERVICE_VERSION} "
        f"on {dp_settings.HOST}:{dp_settings.PORT}"
    )
    yield
    logger.info(f"Shutting down {dp_settings.SERVICE_NAME}")


app = FastAPI(
    title="Sylloge Data Processing Service",
    description="Offline air-gapped data ingestion, row quarantine, and canonical normalization service.",
    version=dp_settings.SERVICE_VERSION,
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

# Error handlers
@app.exception_handler(SATSAError)
async def custom_error_handler(request: Request, exc: SATSAError):
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
app.include_router(ingest_router)
app.include_router(normalize_router)
app.include_router(mapping_router)
app.include_router(quarantine_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=dp_settings.HOST,
        port=dp_settings.PORT,
        reload=settings.DEBUG,
    )
