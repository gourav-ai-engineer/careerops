from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.candidate_profile_store import CandidateProfileStore
from app.database import get_db
from app.job_fit import score_job_fit
from app.job_intake import upsert_job
from app.models import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])
profile_store = CandidateProfileStore()


class JobIntakeRequest(BaseModel):
    company_name: str
    company_domain: str | None = None
    title: str
    location: str | None = None
    role_family: str | None = None
    application_url: HttpUrl | None = None
    source_url: HttpUrl | None = None
    eligibility: str | None = None
    priority: str | None = None


class JobIntakeResponse(BaseModel):
    id: int
    company_id: int
    created: bool
    fingerprint: str
    status: str


class JobFitRequest(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    candidate_skills: list[str] = Field(default_factory=list)
    eligibility_match: bool | None = None
    location_match: bool | None = None


class ProfileJobFitRequest(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    eligibility_match: bool | None = None
    location_match: bool | None = None


class JobFitResponse(BaseModel):
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    eligibility_match: bool | None
    location_match: bool | None
    explanation: str


@router.post("/intake", response_model=JobIntakeResponse, status_code=201)
def intake_job(payload: JobIntakeRequest, db: Session = Depends(get_db)) -> JobIntakeResponse:
    result = upsert_job(
        db,
        company_name=payload.company_name,
        company_domain=payload.company_domain,
        title=payload.title,
        location=payload.location,
        role_family=payload.role_family,
        application_url=str(payload.application_url) if payload.application_url else None,
        source_url=str(payload.source_url) if payload.source_url else None,
        eligibility=payload.eligibility,
        priority=payload.priority,
    )
    return JobIntakeResponse(
        id=result.job.id,
        company_id=result.job.company_id,
        created=result.created,
        fingerprint=result.fingerprint,
        status=result.job.status,
    )


def _fit_response(result) -> JobFitResponse:
    return JobFitResponse(
        score=result.score,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        eligibility_match=result.eligibility_match,
        location_match=result.location_match,
        explanation=result.explanation,
    )


@router.post("/fit-score", response_model=JobFitResponse)
def calculate_fit_score(payload: JobFitRequest) -> JobFitResponse:
    result = score_job_fit(
        payload.required_skills,
        payload.candidate_skills,
        payload.eligibility_match,
        payload.location_match,
    )
    return _fit_response(result)


@router.post("/{job_id}/fit-score/profile", response_model=JobFitResponse)
def calculate_profile_fit_score(
    job_id: int,
    payload: ProfileJobFitRequest,
    db: Session = Depends(get_db),
) -> JobFitResponse:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = profile_store.load(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    result = score_job_fit(
        payload.required_skills,
        profile.skills,
        payload.eligibility_match,
        payload.location_match,
    )
    return _fit_response(result)
