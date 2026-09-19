from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.job_verification import verify_job_source
from app.models import Job, JobSourceEvidence

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobVerificationRequest(BaseModel):
    application_url: HttpUrl | None = None
    source_url: HttpUrl | None = None


class JobVerificationResponse(BaseModel):
    status: str
    reason: str


class SourceEvidenceRequest(BaseModel):
    source_url: HttpUrl
    source_type: str = "source"
    verification_status: str | None = None
    verification_reason: str | None = None


class SourceEvidenceResponse(BaseModel):
    id: int
    job_id: int
    source_url: str
    source_type: str
    verification_status: str
    verification_reason: str
    checked_at: datetime


@router.post("/verify-source", response_model=JobVerificationResponse)
def verify_source(payload: JobVerificationRequest) -> JobVerificationResponse:
    result = verify_job_source(
        str(payload.application_url) if payload.application_url else None,
        str(payload.source_url) if payload.source_url else None,
    )
    return JobVerificationResponse(status=result.status, reason=result.reason)


@router.post("/{job_id}/source-evidence", response_model=SourceEvidenceResponse, status_code=201)
def add_source_evidence(
    job_id: int,
    payload: SourceEvidenceRequest,
    db: Session = Depends(get_db),
) -> JobSourceEvidence:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    company = job.company
    screened = verify_job_source(
        str(payload.source_url),
        str(payload.source_url),
        company.domain if company else None,
    )
    status = payload.verification_status or screened.status
    reason = payload.verification_reason or screened.reason

    evidence = JobSourceEvidence(
        job_id=job_id,
        source_url=str(payload.source_url),
        source_type=payload.source_type,
        verification_status=status,
        verification_reason=reason,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence
