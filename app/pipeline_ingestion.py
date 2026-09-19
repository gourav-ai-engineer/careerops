from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.job_deduplication import compare_jobs
from app.job_extraction import ExtractedJob, extract_jobs
from app.job_intake import upsert_job
from app.models import Company, Job


@dataclass(frozen=True)
class PipelineItem:
    extracted: ExtractedJob
    persisted: bool
    duplicate: bool
    duplicate_confidence: float
    reason: str


def process_text(db: Session, text: str) -> list[PipelineItem]:
    extraction = extract_jobs(text)
    results: list[PipelineItem] = []

    for item in extraction.jobs:
        existing = list(
            db.scalars(
                select(Job).join(Company).where(Company.normalized_name == item.company_name.strip().lower())
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
                break

        if duplicate:
            results.append(PipelineItem(item, False, True, confidence, reason))
            continue

        upsert_job(
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
        results.append(PipelineItem(item, True, False, confidence, "Persisted new job"))

    return results
