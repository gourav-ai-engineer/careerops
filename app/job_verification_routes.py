from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from app.job_verification import verify_job_source

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobVerificationRequest(BaseModel):
    application_url: HttpUrl | None = None
    source_url: HttpUrl | None = None


class JobVerificationResponse(BaseModel):
    status: str
    reason: str


@router.post("/verify-source", response_model=JobVerificationResponse)
def verify_source(payload: JobVerificationRequest) -> JobVerificationResponse:
    result = verify_job_source(
        str(payload.application_url) if payload.application_url else None,
        str(payload.source_url) if payload.source_url else None,
    )
    return JobVerificationResponse(status=result.status, reason=result.reason)
