from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.job_intake import upsert_job


@dataclass(frozen=True)
class IngestedJob:
    company_name: str
    title: str
    location: str | None = None
    application_url: str | None = None
    source_url: str | None = None
    raw_text: str | None = None


URL_RE = re.compile(r"https?://[^\s>]+", re.IGNORECASE)
WHATSAPP_RE = re.compile(r"^\[?\d{1,2}[/-]\d{1,2}[/-]\d{2,4},?\s+[^]]+\]?\s+-\s+", re.MULTILINE)


def _first(row: dict[str, str], *names: str) -> str | None:
    lowered = {str(k).strip().lower(): (v or "").strip() for k, v in row.items()}
    for name in names:
        value = lowered.get(name)
        if value:
            return value
    return None


def parse_csv_jobs(content: str) -> list[IngestedJob]:
    jobs: list[IngestedJob] = []
    for row in csv.DictReader(io.StringIO(content)):
        company = _first(row, "company", "company_name", "employer")
        title = _first(row, "title", "job_title", "role", "position")
        if not company or not title:
            continue
        jobs.append(IngestedJob(company_name=company, title=title,
                                location=_first(row, "location", "city"),
                                application_url=_first(row, "application_url", "apply_url", "url"),
                                source_url=_first(row, "source_url", "source")))
    return jobs


def parse_whatsapp_export(content: str) -> list[IngestedJob]:
    jobs: list[IngestedJob] = []
    for raw_line in content.splitlines():
        line = WHATSAPP_RE.sub("", raw_line).strip()
        if not line or line.startswith("Messages and calls"):
            continue
        urls = URL_RE.findall(line)
        text = URL_RE.sub("", line).strip(" -–—")
        parts = [part.strip() for part in text.split("|")]
        if len(parts) < 2:
            continue
        company, title = parts[0], parts[1]
        if not company or not title:
            continue
        jobs.append(IngestedJob(company_name=company, title=title,
                                location=parts[2] if len(parts) > 2 and parts[2] else None,
                                application_url=urls[0] if urls else None,
                                raw_text=raw_line))
    return jobs


def persist_jobs(db: Session, jobs: list[IngestedJob], source_url: str | None = None) -> dict[str, int]:
    created = 0
    updated = 0
    for item in jobs:
        result = upsert_job(db, company_name=item.company_name, company_domain=None,
                            title=item.title, location=item.location, role_family=None,
                            application_url=item.application_url,
                            source_url=item.source_url or source_url,
                            eligibility=None, priority=None)
        if result.created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "total": len(jobs)}
