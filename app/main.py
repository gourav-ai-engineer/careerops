import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.candidate_profile_routes import router as candidate_profile_router
from app.contact_admin_routes import router as contact_admin_router
from app.contact_routes import router as contact_router
from app.dashboard_routes import router as dashboard_router
from app.extraction_routes import router as extraction_router
from app.ingestion_routes import router as ingestion_router
from app.job_routes import router as job_router
from app.job_verification_routes import router as job_verification_router
from app.live_verification_routes import router as live_verification_router
from app.middleware import api_key_middleware, request_context_middleware
from app.pipeline_routes import router as pipeline_router
from app.resume_routes import router as resume_router
from app.run_routes import router as run_router
from app.smartsheet_routes import router as smartsheet_router
from app.settings import settings

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Career intelligence API for jobs, verification, fit, public contacts, resumes, and Smartsheet synchronization.",
)

app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(api_key_middleware)
app.middleware("http")(request_context_middleware)

app.include_router(candidate_profile_router)
app.include_router(contact_router)
app.include_router(contact_admin_router)
app.include_router(dashboard_router)
app.include_router(extraction_router)
app.include_router(ingestion_router)
app.include_router(job_router)
app.include_router(job_verification_router)
app.include_router(live_verification_router)
app.include_router(pipeline_router)
app.include_router(resume_router)
app.include_router(run_router)
app.include_router(smartsheet_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "careerops", "status": "ok", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "careerops"}


@app.get("/health/db", tags=["system"])
def database_health_check() -> dict[str, str]:
    from sqlalchemy import text
    from app.database import engine
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok", "service": "careerops", "database": "ok"}
