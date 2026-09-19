from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.candidate_fit import (
    VERIFIABLE_JOB_STATUSES,
    assess_candidate_fit,
    persist_fit_assessment,
)
from app.candidate_profile_store import CandidateProfileStore
from app.database import get_db
from app.job_fit import score_job_fit
from app.job_intake import upsert_job
from app.job_query import search_jobs
from app.job_status import ALLOWED_STATUSES, change_job_status
from app.models import CandidateProfileRecord, Job, JobFitAssessment

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


class JobListItem(BaseModel):
    id: int
    company_id: int
    company_name: str
    title: str
    location: str | None
    role_family: str | None
    application_url: str | None
    source_url: str | None
    eligibility: str | None
    priority: str | None
    status: str


class JobListResponse(BaseModel):
    items: list[JobListItem]
    total: int
    page: int
    page_size: int
    pages: int


class JobEvidenceResponse(BaseModel):
    id: int
    source_url: str
    source_type: str
    verification_status: str
    verification_reason: str
    checked_at: datetime | None


class JobStatusHistoryResponse(BaseModel):
    id: int
    from_status: str | None
    to_status: str
    reason: str | None
    changed_at: datetime | None


class JobDetailResponse(BaseModel):
    id: int
    company_id: int
    company_name: str
    company_domain: str | None
    title: str
    location: str | None
    role_family: str | None
    application_url: str | None
    source_url: str | None
    eligibility: str | None
    priority: str | None
    status: str
    first_seen_at: datetime | None
    last_checked_at: datetime | None
    source_evidence: list[JobEvidenceResponse]
    status_history: list[JobStatusHistoryResponse]


class JobStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    reason: str | None = Field(default=None, max_length=2000)


class JobStatusUpdateResponse(BaseModel):
    job_id: int
    previous_status: str
    status: str
    reason: str | None
    changed_at: datetime | None


class FitAssessmentResponse(BaseModel):
    id: int
    job_id: int
    candidate_profile_id: int
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    role_match: bool | None
    location_match: bool | None
    eligibility_match: bool | None
    explanation: str
    evaluation_method: str
    assessed_at: datetime | None


class BulkFitAssessmentResponse(BaseModel):
    assessed: int
    skipped: int
    items: list[FitAssessmentResponse]


def _fit_response(result) -> JobFitResponse:
    return JobFitResponse(
        score=result.score,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        eligibility_match=result.eligibility_match,
        location_match=result.location_match,
        explanation=result.explanation,
    )


def _assessment_response(assessment: JobFitAssessment) -> FitAssessmentResponse:
    return FitAssessmentResponse(
        id=assessment.id,
        job_id=assessment.job_id,
        candidate_profile_id=assessment.candidate_profile_id,
        score=assessment.score,
        matched_skills=json.loads(assessment.matched_skills),
        missing_skills=json.loads(assessment.missing_skills),
        role_match=assessment.role_match,
        location_match=assessment.location_match,
        eligibility_match=assessment.eligibility_match,
        explanation=assessment.explanation,
        evaluation_method=assessment.evaluation_method,
        assessed_at=assessment.assessed_at,
    )


def _profile_record(db: Session) -> CandidateProfileRecord:
    record = db.scalar(select(CandidateProfileRecord).where(CandidateProfileRecord.id == 1))
    if record is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return record


def _assert_assessable(job: Job) -> None:
    if job.status not in VERIFIABLE_JOB_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Fit assessment requires a verified or later-stage job",
        )


@router.get("", response_model=JobListResponse)
def list_jobs(company: str | None = None, title: str | None = None,
              status: str | None = None, role_family: str | None = None,
              location: str | None = None, priority: str | None = None,
              page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100),
              db: Session = Depends(get_db)) -> JobListResponse:
    result = search_jobs(db, company=company, title=title, status=status,
                         role_family=role_family, location=location, priority=priority,
                         page=page, page_size=page_size)
    items = [JobListItem(id=job.id, company_id=job.company_id, company_name=job.company.name,
                         title=job.title, location=job.location, role_family=job.role_family,
                         application_url=job.application_url, source_url=job.source_url,
                         eligibility=job.eligibility, priority=job.priority, status=job.status)
             for job in result.items]
    pages = (result.total + page_size - 1) // page_size if result.total else 0
    return JobListResponse(items=items, total=result.total, page=page,
                           page_size=page_size, pages=pages)


@router.get("/statuses")
def list_job_statuses() -> dict[str, list[str]]:
    return {"statuses": sorted(ALLOWED_STATUSES)}


@router.get("/fit-assessments/verified", response_model=BulkFitAssessmentResponse)
def list_saved_fit_assessments(
    db: Session = Depends(get_db),
) -> BulkFitAssessmentResponse:
    assessments = list(
        db.scalars(
            select(JobFitAssessment)
            .where(JobFitAssessment.candidate_profile_id == 1)
            .order_by(JobFitAssessment.assessed_at.desc())
        )
    )
    return BulkFitAssessmentResponse(
        assessed=len(assessments),
        skipped=0,
        items=[_assessment_response(item) for item in assessments],
    )


@router.post("/fit-assessments/verified", response_model=BulkFitAssessmentResponse)
def assess_verified_jobs(db: Session = Depends(get_db)) -> BulkFitAssessmentResponse:
    _profile_record(db)
    jobs = list(
        db.scalars(
            select(Job)
            .options(selectinload(Job.requirements))
            .where(Job.status.in_(VERIFIABLE_JOB_STATUSES))
            .order_by(Job.first_seen_at.desc(), Job.id.desc())
        )
    )
    items: list[FitAssessmentResponse] = []
    for job in jobs:
        result = assess_candidate_fit(
            job,
            profile_store.load(db),
        )
        profile_record = _profile_record(db)
        assessment = persist_fit_assessment(db, job, profile_record, result)
        items.append(_assessment_response(assessment))
    return BulkFitAssessmentResponse(assessed=len(items), skipped=0, items=items)


@router.post("/{job_id}/fit-assessment", response_model=FitAssessmentResponse)
def assess_job_fit(job_id: int, db: Session = Depends(get_db)) -> FitAssessmentResponse:
    job = db.scalar(
        select(Job)
        .options(selectinload(Job.requirements))
        .where(Job.id == job_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    _assert_assessable(job)
    profile_record = _profile_record(db)
    profile = profile_store.load(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    result = assess_candidate_fit(job, profile)
    assessment = persist_fit_assessment(db, job, profile_record, result)
    return _assessment_response(assessment)


@router.get("/{job_id}/fit-assessment", response_model=FitAssessmentResponse)
def get_job_fit_assessment(job_id: int, db: Session = Depends(get_db)) -> FitAssessmentResponse:
    assessment = db.scalar(
        select(JobFitAssessment)
        .where(
            JobFitAssessment.job_id == job_id,
            JobFitAssessment.candidate_profile_id == 1,
        )
        .order_by(JobFitAssessment.assessed_at.desc())
    )
    if assessment is None:
        raise HTTPException(status_code=404, detail="Fit assessment not found")
    return _assessment_response(assessment)


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetailResponse:
    job = db.scalar(
        select(Job)
        .options(selectinload(Job.source_evidence), selectinload(Job.status_history))
        .where(Job.id == job_id)
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobDetailResponse(
        id=job.id,
        company_id=job.company_id,
        company_name=job.company.name,
        company_domain=job.company.domain,
        title=job.title,
        location=job.location,
        role_family=job.role_family,
        application_url=job.application_url,
        source_url=job.source_url,
        eligibility=job.eligibility,
        priority=job.priority,
        status=job.status,
        first_seen_at=job.first_seen_at,
        last_checked_at=job.last_checked_at,
        source_evidence=[
            JobEvidenceResponse(
                id=evidence.id,
                source_url=evidence.source_url,
                source_type=evidence.source_type,
                verification_status=evidence.verification_status,
                verification_reason=evidence.verification_reason,
                checked_at=evidence.checked_at,
            )
            for evidence in job.source_evidence
        ],
        status_history=[
            JobStatusHistoryResponse(
                id=history.id,
                from_status=history.from_status,
                to_status=history.to_status,
                reason=history.reason,
                changed_at=history.changed_at,
            )
            for history in job.status_history
        ],
    )


@router.patch("/{job_id}/status", response_model=JobStatusUpdateResponse)
def update_job_status(job_id: int, payload: JobStatusUpdateRequest,
                      db: Session = Depends(get_db)) -> JobStatusUpdateResponse:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    previous_status = job.status
    try:
        result = change_job_status(db, job, payload.status, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return JobStatusUpdateResponse(
        job_id=result.job.id,
        previous_status=previous_status,
        status=result.job.status,
        reason=result.history.reason,
        changed_at=result.history.changed_at,
    )


@router.post("/intake", response_model=JobIntakeResponse, status_code=201)
def intake_job(payload: JobIntakeRequest, db: Session = Depends(get_db)) -> JobIntakeResponse:
    result = upsert_job(db, company_name=payload.company_name, company_domain=payload.company_domain,
                        title=payload.title, location=payload.location, role_family=payload.role_family,
                        application_url=str(payload.application_url) if payload.application_url else None,
                        source_url=str(payload.source_url) if payload.source_url else None,
                        eligibility=payload.eligibility, priority=payload.priority)
    return JobIntakeResponse(id=result.job.id, company_id=result.job.company_id, created=result.created,
                             fingerprint=result.fingerprint, status=result.job.status)


@router.post("/fit-score", response_model=JobFitResponse)
def calculate_fit_score(payload: JobFitRequest) -> JobFitResponse:
    return _fit_response(score_job_fit(payload.required_skills, payload.candidate_skills,
                                       payload.eligibility_match, payload.location_match))


@router.post("/{job_id}/fit-score/profile", response_model=JobFitResponse)
def calculate_profile_fit_score(job_id: int, payload: ProfileJobFitRequest,
                                db: Session = Depends(get_db)) -> JobFitResponse:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    profile = profile_store.load(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return _fit_response(score_job_fit(payload.required_skills, profile.skills,
                                       payload.eligibility_match, payload.location_match))
