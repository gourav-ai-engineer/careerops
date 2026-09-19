from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from pydantic import BaseModel, Field


class ExtractedJob(BaseModel):
    company_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str | None = None
    application_url: str | None = None
    source_url: str | None = None
    role_family: str | None = None
    eligibility: str | None = None
    required_skills: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    extraction_method: str = "heuristic"


@dataclass(frozen=True)
class ExtractionResult:
    jobs: list[ExtractedJob]
    warnings: list[str]


URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
SKILL_TERMS = ("python", "java", "c++", "sql", "pytorch", "tensorflow", "aws", "docker", "fastapi", "kubernetes", "react", "machine learning", "deep learning")


def _clean_url(value: str) -> str:
    return value.rstrip(".,);]")


def _skills(text: str) -> list[str]:
    lowered = text.casefold()
    return [term for term in SKILL_TERMS if term in lowered]


def extract_jobs(text: str) -> ExtractionResult:
    """Extract predictable job records without requiring an external LLM.

    This is the safe baseline adapter; an LLM provider can later implement the same schema.
    Expected line format: Company | Title | Location [URL].
    """
    jobs: list[ExtractedJob] = []
    warnings: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Messages and calls"):
            continue
        urls = [_clean_url(url) for url in URL_RE.findall(line)]
        body = URL_RE.sub("", line).strip(" -–—")
        parts = [part.strip() for part in body.split("|")]
        if len(parts) < 2:
            continue
        company, title = parts[0], parts[1]
        location = parts[2] if len(parts) > 2 and parts[2] else None
        jobs.append(ExtractedJob(company_name=company, title=title, location=location,
                                 application_url=urls[0] if urls else None,
                                 required_skills=_skills(line), confidence=0.75))
    if not jobs:
        warnings.append("No pipe-delimited job records were detected")
    return ExtractionResult(jobs=jobs, warnings=warnings)
