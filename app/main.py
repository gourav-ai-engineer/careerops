from fastapi import FastAPI

from app.candidate_profile_routes import router as candidate_profile_router
from app.contact_routes import router as contact_router
from app.extraction_routes import router as extraction_router
from app.ingestion_routes import router as ingestion_router
from app.job_routes import router as job_router
from app.job_verification_routes import router as job_verification_router
from app.pipeline_routes import router as pipeline_router

app = FastAPI(
    title="CareerOps",
    version="1.0.0",
    description="Job and recruiter intelligence pipeline.",
)

app.include_router(candidate_profile_router)
app.include_router(contact_router)
app.include_router(extraction_router)
app.include_router(ingestion_router)
app.include_router(job_router)
app.include_router(job_verification_router)
app.include_router(pipeline_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Provide a discoverable service entry point."""
    return {"service": "careerops", "status": "ok", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a basic service health response."""
    return {"status": "ok", "service": "careerops"}
