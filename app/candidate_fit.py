from __future__ import annotations

import json
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.candidate_profile import CandidateProfile
from app.models import CandidateProfileRecord, Job, JobFitAssessment


VERIFIABLE_JOB_STATUSES = frozenset(
    {"verified", "shortlisted", "applied", "interview", "offer"}
)


@dataclass(frozen=True)
class CandidateFitResult:
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    role_match: bool | None
    location_match: bool | None
    eligibility_match: bool | None
    explanation: str
    evaluation_method: str = "rule_based_v1"


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def _match_terms(required: list[str], candidate: list[str]) -> tuple[list[str], list[str]]:
    candidate_norm = {_norm(value) for value in candidate if _norm(value)}
    matched: list[str] = []
    missing: list[str] = []
    for value in required:
        normalized = _norm(value)
        if not normalized:
            continue
        found = normalized in candidate_norm or any(
            normalized in candidate_item or candidate_item in normalized
            for candidate_item in candidate_norm
        )
        (matched if found else missing).append(value.strip())
    return sorted(set(matched), key=str.casefold), sorted(set(missing), key=str.casefold)


def _role_match(job: Job, profile: CandidateProfile) -> bool | None:
    if not job.role_family or not profile.target_role_families:
        return None
    job_role = _norm(job.role_family)
    targets = [_norm(value) for value in profile.target_role_families]
    return any(job_role == target or job_role in target or target in job_role for target in targets)


def _location_match(job: Job, profile: CandidateProfile) -> bool | None:
    if not job.location or not profile.preferred_locations:
        return None
    location = _norm(job.location)
    preferred = [_norm(value) for value in profile.preferred_locations]
    if "remote" in location:
        return any("remote" in value for value in preferred)
    return any(location == value or location in value or value in location for value in preferred)


def _eligibility_match(job: Job, profile: CandidateProfile) -> bool | None:
    if not job.eligibility or not profile.work_authorization:
        return None
    eligibility = _norm(job.eligibility)
    authorization = _norm(profile.work_authorization)
    return authorization in eligibility or eligibility in authorization


def assess_candidate_fit(
    job: Job,
    profile: CandidateProfile,
    required_skills: list[str] | None = None,
) -> CandidateFitResult:
    skills = required_skills
    if skills is None:
        skills = json.loads(job.requirements.required_skills) if job.requirements else []

    matched, missing = _match_terms(skills, profile.skills)
    role_match = _role_match(job, profile)
    location_match = _location_match(job, profile)
    eligibility_match = _eligibility_match(job, profile)

    skill_total = len(matched) + len(missing)
    skill_score = round((len(matched) / skill_total) * 50) if skill_total else 25
    role_score = 20 if role_match is True else 0 if role_match is False else 10
    location_score = 15 if location_match is True else 0 if location_match is False else 7
    eligibility_score = 15 if eligibility_match is True else 0 if eligibility_match is False else 7
    score = min(100, skill_score + role_score + location_score + eligibility_score)

    explanation = (
        f"Skills matched {len(matched)}/{skill_total}; "
        f"role_match={role_match}; location_match={location_match}; "
        f"eligibility_match={eligibility_match}. Rule-based assessment; "
        f"unknown dimensions receive partial credit rather than being treated as a mismatch."
    )
    return CandidateFitResult(
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        role_match=role_match,
        location_match=location_match,
        eligibility_match=eligibility_match,
        explanation=explanation,
    )


def persist_fit_assessment(
    db: Session,
    job: Job,
    profile_record: CandidateProfileRecord,
    result: CandidateFitResult,
) -> JobFitAssessment:
    assessment = db.scalar(
        select(JobFitAssessment).where(
            JobFitAssessment.job_id == job.id,
            JobFitAssessment.candidate_profile_id == profile_record.id,
        )
    )
    if assessment is None:
        assessment = JobFitAssessment(
            job_id=job.id,
            candidate_profile_id=profile_record.id,
        )
        db.add(assessment)

    assessment.score = result.score
    assessment.matched_skills = json.dumps(result.matched_skills)
    assessment.missing_skills = json.dumps(result.missing_skills)
    assessment.role_match = result.role_match
    assessment.location_match = result.location_match
    assessment.eligibility_match = result.eligibility_match
    assessment.explanation = result.explanation
    assessment.evaluation_method = result.evaluation_method
    db.commit()
    db.refresh(assessment)
    return assessment
