from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str


OFFICIAL_HOST_HINTS = (
    "careers.",
    "jobs.",
)


def verify_job_source(application_url: str | None, source_url: str | None) -> VerificationResult:
    """Perform conservative URL-level screening; human/source review remains required."""
    candidate = application_url or source_url
    if not candidate:
        return VerificationResult("needs_review", "No application or source URL supplied")

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return VerificationResult("rejected", "URL must use HTTP(S) and include a host")

    host = parsed.netloc.lower().split(":", 1)[0]
    if any(hint in host for hint in OFFICIAL_HOST_HINTS):
        return VerificationResult("screened", "Host resembles a careers or jobs subdomain; verify ownership")

    return VerificationResult("needs_review", "URL format is valid but ownership was not verified")
