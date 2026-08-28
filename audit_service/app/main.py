"""FastAPI Application Entrypoint for SAT-SA Audit Service Microservice (Port 8003)."""

import contextlib
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.errors import SATSAError
from shared.logging import logger
from .config import audit_settings
from .routers import health_router, manifest_router


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(
        f"Starting {audit_settings.SERVICE_NAME} v{audit_settings.SERVICE_VERSION} "
        f"on {audit_settings.HOST}:{audit_settings.PORT}"
    )
    yield
    logger.info(f"Shutting down {audit_settings.SERVICE_NAME}")


app = FastAPI(
    title="Sylloge Cryptographic Audit Service",
    description="Offline air-gapped immutable SHA-256 Merkle root manifest generator and tamper verification service.",
    version=audit_settings.SERVICE_VERSION,
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
app.include_router(manifest_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=audit_settings.HOST,
        port=audit_settings.PORT,
        reload=settings.DEBUG,
    )
