"""FastAPI Application Entrypoint for SAT-SA Backend API Gateway Microservice (Port 8000)."""

import contextlib
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from shared.config import settings
from shared.errors import SATSAError
from shared.logging import logger
from .config import backend_settings
from .routers import (
    auth_router,
    benchmarks_router,
    dashboard_router,
    entities_router,
    findings_router,
    health_router,
    pipeline_router,
    reports_router,
    submissions_router,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info(
        f"Starting {backend_settings.SERVICE_NAME} v{backend_settings.SERVICE_VERSION} "
        f"on {backend_settings.HOST}:{backend_settings.PORT}"
    )
    try:
        from shared.db.session import init_db_schema
        await init_db_schema()
        logger.info("Database schema initialized successfully.")
    except Exception as exc:
        logger.warning(f"Database schema initialization deferred: {exc}")
    yield
    logger.info(f"Shutting down {backend_settings.SERVICE_NAME}")


app = FastAPI(
    title="Sylloge Backend API Gateway",
    description="Offline air-gapped supervisory cybersecurity analytics platform API gateway.",
    version=backend_settings.SERVICE_VERSION,
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
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(entities_router)
app.include_router(findings_router)
app.include_router(submissions_router)
app.include_router(benchmarks_router)
app.include_router(reports_router)
app.include_router(pipeline_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=backend_settings.HOST,
        port=backend_settings.PORT,
        reload=settings.DEBUG,
    )
