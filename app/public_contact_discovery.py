from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)"
)
MAX_SOURCE_URLS = 20


@dataclass(frozen=True)
class PublicPhoneCandidate:
    phone: str
    source_url: str
    phone_type: str = "unknown_public_business"
    confidence: str = "low"


def _same_or_subdomain(hostname: str, allowed_domain: str) -> bool:
    host = hostname.lower().split(":", 1)[0]
    domain = allowed_domain.lower().removeprefix("www.").strip().rstrip("/")
    return host == domain or host.endswith(f".{domain}")


def ensure_allowed_source(source_url: str, allowed_domain: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS sources are accepted.")
    if not _same_or_subdomain(parsed.hostname, allowed_domain):
        raise ValueError("Source must belong to the supplied company domain or a subdomain.")


def normalize_phone(raw: str) -> str:
    compact = re.sub(r"\s+", " ", raw).strip()
    return compact


def extract_phone_candidates(text: str, source_url: str) -> list[PublicPhoneCandidate]:
    results: list[PublicPhoneCandidate] = []
    seen: set[str] = set()
    for match in PHONE_PATTERN.findall(text):
        phone = normalize_phone(match)
        digits = re.sub(r"\D", "", phone)
        if not 8 <= len(digits) <= 15:
            continue
        if phone in seen:
            continue
        seen.add(phone)
        results.append(PublicPhoneCandidate(phone=phone, source_url=source_url))
    return results


async def discover_public_phones(
    source_urls: list[str],
    allowed_domain: str,
    timeout_seconds: float = 10.0,
) -> list[PublicPhoneCandidate]:
    if not source_urls:
        return []
    if len(source_urls) > MAX_SOURCE_URLS:
        raise ValueError(f"A maximum of {MAX_SOURCE_URLS} source URLs is allowed per request.")

    candidates: list[PublicPhoneCandidate] = []
    async with httpx.AsyncClient(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "CareerOps-PublicContactResearch/0.1"},
    ) as client:
        for source_url in source_urls:
            ensure_allowed_source(source_url, allowed_domain)
            response = await client.get(source_url)
            response.raise_for_status()
            # Validate the final URL too, preventing redirects to unrelated domains.
            ensure_allowed_source(str(response.url), allowed_domain)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                continue
            candidates.extend(extract_phone_candidates(response.text, str(response.url)))

    unique: dict[tuple[str, str], PublicPhoneCandidate] = {
        (item.phone, item.source_url): item for item in candidates
    }
    return list(unique.values())
