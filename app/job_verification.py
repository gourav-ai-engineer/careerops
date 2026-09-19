from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str


OFFICIAL_HOST_HINTS = ("careers.", "jobs.")


def _host(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").lower().strip(".")


def host_matches_domain(url: str | None, company_domain: str | None) -> bool:
    """Return true only for the company domain or one of its subdomains."""
    candidate = _host(url)
    domain = _host(company_domain)
    return bool(candidate and domain and (candidate == domain or candidate.endswith(f".{domain}")))


def verify_job_source(
    application_url: str | None,
    source_url: str | None,
    company_domain: str | None = None,
) -> VerificationResult:
    """Perform conservative URL screening; this does not prove ownership or authenticity."""
    candidate = application_url or source_url
    if not candidate:
        return VerificationResult("needs_review", "No application or source URL supplied")

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return VerificationResult("rejected", "URL must use HTTP(S) and include a host")

    host = _host(candidate)
    if company_domain and host_matches_domain(candidate, company_domain):
        return VerificationResult("screened", "URL host matches the stored company domain; verify the specific job")

    if any(hint in host for hint in OFFICIAL_HOST_HINTS):
        return VerificationResult("screened", "Host resembles a careers or jobs subdomain; verify ownership")

    return VerificationResult("needs_review", "URL format is valid but company-domain ownership was not verified")
