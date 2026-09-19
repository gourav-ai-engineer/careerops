from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.job_verification import host_matches_domain


@dataclass(frozen=True)
class OfficialVerificationResult:
    status: str
    reason: str
    candidate_host: str
    company_host: str


def normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").lower().strip(".")


def verify_official_domain(application_url: str | None, company_domain: str | None) -> OfficialVerificationResult:
    candidate_host = normalize_domain(application_url)
    company_host = normalize_domain(company_domain)
    if not candidate_host:
        return OfficialVerificationResult("needs_review", "Application URL has no valid host", candidate_host, company_host)
    if not company_host:
        return OfficialVerificationResult("needs_review", "Company domain is missing", candidate_host, company_host)
    if host_matches_domain(application_url, company_domain):
        return OfficialVerificationResult("screened", "Application host matches the company domain or subdomain; ownership still requires verification", candidate_host, company_host)
    return OfficialVerificationResult("needs_review", "Application host differs from the company domain; review the employer's authorized ATS or redirect", candidate_host, company_host)
