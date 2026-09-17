import pytest

from app.public_contact_discovery import (
    MAX_SOURCE_URLS,
    discover_public_phones,
    ensure_allowed_source,
    extract_phone_candidates,
)


def test_extracts_and_deduplicates_phone_candidates() -> None:
    text = "Call +91 98765 43210 or +91 98765 43210. Office: 0124-4001234"
    results = extract_phone_candidates(text, "https://example.com/contact")

    assert len(results) == 2
    assert results[0].source_url == "https://example.com/contact"


def test_rejects_non_https_sources() -> None:
    with pytest.raises(ValueError):
        ensure_allowed_source("http://example.com/contact", "example.com")


def test_rejects_external_domains() -> None:
    with pytest.raises(ValueError):
        ensure_allowed_source("https://other.example/contact", "example.com")


def test_accepts_company_subdomain() -> None:
    ensure_allowed_source("https://careers.example.com/contact", "example.com")


@pytest.mark.asyncio
async def test_rejects_too_many_source_urls() -> None:
    with pytest.raises(ValueError, match="maximum"):
        await discover_public_phones(
            ["https://example.com/contact"] * (MAX_SOURCE_URLS + 1),
            "example.com",
        )
