"""Safety-first helpers for publicly published professional contact data.

This module deliberately does not scrape private profiles, bypass logins, infer
phone numbers, or classify personal mobile numbers as recruiting contacts.
"""

from dataclasses import dataclass
from urllib.parse import urlparse


ALLOWED_PHONE_TYPES = {
    "company_switchboard",
    "official_recruitment_helpline",
    "public_work_phone",
}

VALIDATION_STATUSES = {"unverified", "source_checked", "verified", "rejected"}


@dataclass(frozen=True, slots=True)
class PublicContactCandidate:
    name: str | None
    title: str | None
    phone: str | None
    phone_type: str | None
    source_url: str
    verification_status: str = "unverified"
    verification_confidence: str | None = None


def is_http_url(value: str) -> bool:
    """Return whether a source is an HTTP(S) URL."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_public_contact(candidate: PublicContactCandidate) -> list[str]:
    """Return validation issues; an empty list means the record passes basic checks."""
    issues: list[str] = []

    if not candidate.source_url or not is_http_url(candidate.source_url):
        issues.append("source_url must be a valid HTTP(S) URL")

    if candidate.verification_status not in VALIDATION_STATUSES:
        issues.append("verification_status is not supported")

    if candidate.phone and candidate.phone_type not in ALLOWED_PHONE_TYPES:
        issues.append("phone_type must describe an allowed professional number")

    if candidate.phone and candidate.verification_status == "unverified":
        issues.append("phone numbers must not be treated as verified before source review")

    if candidate.phone and not candidate.phone.strip():
        issues.append("phone cannot be blank whitespace")

    return issues


def normalize_phone(value: str | None) -> str | None:
    """Normalize whitespace only; do not guess country codes or alter digits."""
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None
