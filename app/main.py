from fastapi import FastAPI

from app.contact_routes import router as contact_router
from app.job_routes import router as job_router

app = FastAPI(
    title="CareerOps",
    version="0.3.0",
    description="Job and recruiter intelligence pipeline.",
)

app.include_router(contact_router)
app.include_router(job_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Provide a discoverable service entry point."""
    return {"service": "careerops", "status": "ok", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a basic service health response."""
    return {"status": "ok", "service": "careerops"}
