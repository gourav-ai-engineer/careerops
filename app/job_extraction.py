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
SKILL_TERMS = (
    "python", "java", "c++", "sql", "pytorch", "tensorflow", "aws",
    "docker", "fastapi", "kubernetes", "react", "machine learning", "deep learning",
)


def _clean_url(value: str) -> str:
    return value.rstrip(".,);]")


def _skills(text: str) -> list[str]:
    lowered = text.casefold()
    return [term for term in SKILL_TERMS if term in lowered]


def _role_family(title: str) -> str | None:
    value = title.casefold()
    if any(term in value for term in ("machine learning", "ml engineer", "ai engineer", "genai", "llm", "deep learning")):
        return "AI/ML"
    if any(term in value for term in ("data scientist", "data science")):
        return "Data Science"
    if any(term in value for term in ("data engineer", "analytics engineer")):
        return "Data Engineering"
    if any(term in value for term in ("backend", "server-side")):
        return "Backend"
    if any(term in value for term in ("frontend", "front-end", "react")):
        return "Frontend"
    if any(term in value for term in ("software engineer", "sde", "developer")):
        return "Software Engineering"
    return None


def extract_jobs(text: str) -> ExtractionResult:
    """Extract predictable job records without requiring an external LLM.

    Supported baseline format: Company | Title | Location [URL].
    A second delimiter such as a WhatsApp export timestamp is not treated as a job.
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
        application_url = urls[0] if urls else None
        # The source evidence is the captured application/source URL. This is evidence only;
        # it does not imply that the URL is an official employer source.
        source_url = application_url
        # Keep the import here so malformed URLs cannot break extraction.
        if application_url:
            _ = urlsplit(application_url).hostname
        jobs.append(
            ExtractedJob(
                company_name=company,
                title=title,
                location=location,
                application_url=application_url,
                source_url=source_url,
                role_family=_role_family(title),
                required_skills=_skills(line),
                confidence=0.75,
            )
        )
    if not jobs:
        warnings.append("No pipe-delimited job records were detected")
    return ExtractionResult(jobs=jobs, warnings=warnings)
