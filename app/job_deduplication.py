from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.job_intake import canonical_url, normalize_text


@dataclass(frozen=True)
class DuplicateDecision:
    is_duplicate: bool
    confidence: float
    reason: str


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def compare_jobs(
    company: str,
    title: str,
    location: str | None,
    application_url: str | None,
    existing_company: str,
    existing_title: str,
    existing_location: str | None,
    existing_application_url: str | None,
) -> DuplicateDecision:
    current_url = canonical_url(application_url)
    previous_url = canonical_url(existing_application_url)

    if current_url and previous_url and current_url == previous_url:
        return DuplicateDecision(True, 1.0, "Canonical application URLs match")

    company_score = _similarity(company, existing_company)
    title_score = _similarity(title, existing_title)
    location_score = _similarity(location or "", existing_location or "")
    confidence = round((company_score * 0.35) + (title_score * 0.5) + (location_score * 0.15), 4)

    duplicate = company_score >= 0.92 and title_score >= 0.88 and (
        not location or not existing_location or location_score >= 0.8
    )
    reason = "Company, title, and location are sufficiently similar" if duplicate else "Records differ"
    return DuplicateDecision(duplicate, confidence, reason)
