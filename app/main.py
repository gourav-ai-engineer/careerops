from fastapi import FastAPI

app = FastAPI(
    title="CareerOps",
    version="0.1.0",
    description="Job and recruiter intelligence pipeline.",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    """Return a basic service health response."""
    return {"status": "ok", "service": "careerops"}
