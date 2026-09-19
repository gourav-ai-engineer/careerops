from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.job_verification import verify_job_source
from app.models import Job, JobSourceEvidence
from app.official_verification import verify_official_domain

router = APIRouter(prefix="/jobs", tags=["jobs"])
VerificationStatus = Literal["screened", "needs_review", "verified", "rejected"]
SourceType = Literal["application", "source", "official_career_page"]


class JobVerificationRequest(BaseModel):
    application_url: HttpUrl | None = None
    source_url: HttpUrl | None = None


class JobVerificationResponse(BaseModel):
    status: str
    reason: str


class OfficialDomainRequest(BaseModel):
    application_url: HttpUrl
    company_domain: str


class OfficialDomainResponse(BaseModel):
    status: str
    reason: str
    candidate_host: str
    company_host: str


class SourceEvidenceRequest(BaseModel):
    source_url: HttpUrl
    source_type: SourceType = "source"
    verification_status: VerificationStatus | None = None
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


@router.post("/verify-official-domain", response_model=OfficialDomainResponse)
def verify_official_domain_route(payload: OfficialDomainRequest) -> OfficialDomainResponse:
    result = verify_official_domain(str(payload.application_url), payload.company_domain)
    return OfficialDomainResponse(status=result.status, reason=result.reason,
                                  candidate_host=result.candidate_host, company_host=result.company_host)


@router.post("/{job_id}/source-evidence", response_model=SourceEvidenceResponse, status_code=201)
def add_source_evidence(
    job_id: int,
    payload: SourceEvidenceRequest,
    db: Session = Depends(get_db),
) -> JobSourceEvidence:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    screened = verify_job_source(str(payload.source_url), str(payload.source_url),
                                 job.company.domain if job.company else None)
    status = payload.verification_status or screened.status
    reason = payload.verification_reason or screened.reason

    evidence = JobSourceEvidence(job_id=job_id, source_url=str(payload.source_url),
                                 source_type=payload.source_type, verification_status=status,
                                 verification_reason=reason)
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/{job_id}/source-evidence", response_model=list[SourceEvidenceResponse])
def list_source_evidence(job_id: int, db: Session = Depends(get_db)) -> list[JobSourceEvidence]:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list(db.scalars(select(JobSourceEvidence).where(JobSourceEvidence.job_id == job_id)
                           .order_by(JobSourceEvidence.checked_at.desc())))
