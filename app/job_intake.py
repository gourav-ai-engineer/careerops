from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Job


@dataclass(frozen=True)
class JobIntakeResult:
    job: Job
    created: bool
    fingerprint: str


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def canonical_url(value: str | None) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


def job_fingerprint(company: str, title: str, location: str | None, application_url: str | None) -> str:
    raw = "|".join((normalize_text(company), normalize_text(title), normalize_text(location), canonical_url(application_url)))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_job(db: Session, *, company_name: str, company_domain: str | None, title: str, location: str | None,
               role_family: str | None, application_url: str | None, source_url: str | None,
               eligibility: str | None, priority: str | None) -> JobIntakeResult:
    normalized_company = normalize_text(company_name)
    company = db.scalar(select(Company).where(Company.normalized_name == normalized_company))
    if company is None:
        company = Company(name=company_name.strip(), normalized_name=normalized_company, domain=company_domain)
        db.add(company)
        db.flush()
    elif company_domain and not company.domain:
        company.domain = company_domain

    job = db.scalar(select(Job).where(Job.company_id == company.id, Job.title == title.strip(), Job.application_url == application_url))
    created = job is None
    if created:
        job = Job(company_id=company.id, title=title.strip(), location=location, role_family=role_family,
                  application_url=application_url, source_url=source_url, eligibility=eligibility,
                  priority=priority, status="discovered")
        db.add(job)
    else:
        for key, value in {"location": location, "role_family": role_family, "source_url": source_url,
                           "eligibility": eligibility, "priority": priority}.items():
            if value is not None:
                setattr(job, key, value)
    db.commit()
    db.refresh(job)
    return JobIntakeResult(job=job, created=created, fingerprint=job_fingerprint(company_name, title, location, application_url))
