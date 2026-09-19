from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.job_deduplication import compare_jobs
from app.job_extraction import ExtractedJob, extract_jobs
from app.job_intake import upsert_job
from app.models import Company, Job, JobRequirement


@dataclass(frozen=True)
class PipelineItem:
    extracted: ExtractedJob
    job_id: int
    persisted: bool
    duplicate: bool
    duplicate_confidence: float
    reason: str


def _upsert_requirements(db: Session, job_id: int, item: ExtractedJob) -> None:
    if not item.required_skills:
        return
    requirement = db.scalar(select(JobRequirement).where(JobRequirement.job_id == job_id))
    if requirement is None:
        requirement = JobRequirement(job_id=job_id)
        db.add(requirement)
    requirement.required_skills = json.dumps(item.required_skills)
    requirement.extraction_method = item.extraction_method
    requirement.confidence = f"{item.confidence:.2f}"
    db.commit()


def process_text(db: Session, text: str) -> list[PipelineItem]:
    extraction = extract_jobs(text)
    results: list[PipelineItem] = []

    for item in extraction.jobs:
        existing = list(
            db.scalars(
                select(Job).join(Company).where(
                    Company.normalized_name == item.company_name.strip().lower()
                )
            )
        )
        duplicate = False
        confidence = 0.0
        reason = "No matching existing job"
        for job in existing:
            decision = compare_jobs(
                item.company_name, item.title, item.location, item.application_url,
                job.company.name, job.title, job.location, job.application_url,
            )
            if decision.is_duplicate:
                duplicate, confidence, reason = True, decision.confidence, decision.reason
                if item.required_skills:
                    _upsert_requirements(db, job.id, item)
                results.append(PipelineItem(item, job.id, False, True, confidence, reason))
                break

        if duplicate:
            continue

        intake = upsert_job(
            db,
            company_name=item.company_name,
            company_domain=None,
            title=item.title,
            location=item.location,
            role_family=item.role_family,
            application_url=item.application_url,
            source_url=item.source_url,
            eligibility=item.eligibility,
            priority=None,
        )
        _upsert_requirements(db, intake.job.id, item)
        results.append(PipelineItem(item, intake.job.id, True, False, confidence, "Persisted new job"))

    return results
