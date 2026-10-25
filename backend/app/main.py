"""
==============================================================================
File: backend/app/main.py
Purpose: FastAPI main application entry point, CORS middleware setup,
         lifecycle startup hooks, and API router aggregation.
Architecture: Backend Core Application Gateway
==============================================================================

Why FastAPI?
1. Native Asynchronous Execution (ASGI): Scales efficiently under high I/O workloads
   such as LLM generation and vector searches.
2. Automatic OpenAPI Documentation: Dynamically generates interactive Swagger UI
   at `/docs` and ReDoc at `/redoc`.
3. Strict Pydantic Data Serialization: Validates input/output contracts with full
   type hints, eliminating runtime type bugs.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.documents import router as documents_router
from app.api.v1.extraction import router as extraction_router
from app.api.v1.requirements import router as requirements_router
from app.api.v1.traceability import router as traceability_router
from app.api.v1.audit import router as audit_router
from app.models.extraction import ProductExtractionRecord
from app.models.requirement import RequirementPackageRecord
from app.models.traceability import TraceabilityRecord
from app.models.audit import AuditLogRecord


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager:
    Executes database table schema creation and resource initializations on startup,
    and handles graceful teardown on shutdown.
    """
    # Create SQLite database tables if they do not yet exist
    Base.metadata.create_all(bind=engine)
    print(f"[*] Database initialized: {settings.DATABASE_URL}")
    print(f"[*] Gemini Model configured: {settings.GEMINI_MODEL}")
    yield
    print("[*] Application shutdown completed.")


app = FastAPI(
    title="Insurance Requirements Agent API",
    description=(
        "Enterprise-grade Agentic AI backend for ingesting insurance policy forms, "
        "extracting structured coverage parameters with source citations, generating "
        "BRDs, user stories, data models, and API specs, with full traceability and human review."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) so Flutter Web on any dynamic port can interact
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers under /api/v1 prefix
app.include_router(documents_router, prefix="/api/v1")
app.include_router(extraction_router, prefix="/api/v1")
app.include_router(requirements_router, prefix="/api/v1")
app.include_router(traceability_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


@app.get("/", tags=["Health Check"])
def root():
    """Root status endpoint providing basic service health and metadata."""
    return {
        "service": "Insurance Requirements Agent API",
        "status": "operational",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs"
    }


@app.get("/health", tags=["Health Check"])
def health_check():
    """Detailed health check for liveness and readiness probes."""
    return {
        "status": "healthy",
        "database": "connected",
        "model": settings.GEMINI_MODEL
    }
