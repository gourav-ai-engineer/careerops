from fastapi import FastAPI

from app.contact_routes import router as contact_router

app = FastAPI(
    title="CareerOps",
    version="0.2.0",
    description="Job and recruiter intelligence pipeline.",
)

app.include_router(contact_router)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a basic service health response."""
    return {"status": "ok", "service": "careerops"}
