"""
NovellaForge - Serial Fiction Studio
Main FastAPI Application
"""
from contextlib import asynccontextmanager
import warnings
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import logging

from app.core.config import settings
from app.api.v1 import api_router
from app.db.session import engine
from app.db.base import Base
from app.infrastructure.di.providers import get_configured_container
from app.infrastructure.di.container import Container
from app.infrastructure.observability import (
    ObservabilityMiddleware,
    PROMETHEUS_AVAILABLE,
    METRICS_CONTENT_TYPE,
    render_metrics,
    configure_structlog,
    setup_tracing,
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)
app_logger = logging.getLogger("app")
app_logger.setLevel(settings.LOG_LEVEL)
app_logger.propagate = True
app_logger.disabled = False

if settings.STRUCTURED_LOGGING_ENABLED:
    configure_structlog()
if settings.TRACING_ENABLED:
    setup_tracing(settings.PROJECT_NAME)

if settings.DEBUG:
    warnings.filterwarnings(
        "ignore",
        message='Field "model_name".*protected namespace',
    )

pipeline_logger = logging.getLogger("app.services.writing_pipeline")
pipeline_logger.setLevel(settings.LOG_LEVEL)
pipeline_logger.propagate = True
pipeline_logger.disabled = False

# Configure rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup application resources."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    container = get_configured_container()
    app.state.container = container

    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    if settings.RAG_PRELOAD_MODELS:
        try:
            from app.services.rag_service import RagService

            rag_service = RagService()
            await rag_service.warmup()
            logger.info("RAG embeddings warmed up")
        except Exception:
            logger.exception("RAG warmup failed")

    yield

    Container.reset()
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


def get_container() -> Container:
    return Container.get_instance()


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Serial Fiction Studio",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Trusted Host Middleware (optional, for production)
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

if settings.OBSERVABILITY_ENABLED:
    app.add_middleware(ObservabilityMiddleware)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=True,
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_host": request.client.host if request.client else None,
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Une erreur interne est survenue",
            "error": str(exc) if settings.DEBUG else None,
            "type": type(exc).__name__ if settings.DEBUG else None
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.APP_ENV
    }


if settings.METRICS_ENABLED and PROMETHEUS_AVAILABLE:
    @app.get(settings.METRICS_PATH, tags=["Metrics"])
    async def metrics():
        return Response(content=render_metrics(), media_type=METRICS_CONTENT_TYPE)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "NovellaForge API - Serial Fiction Studio",
        "version": settings.VERSION,
        "docs": "/api/docs" if settings.DEBUG else None
    }


# Include API router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
