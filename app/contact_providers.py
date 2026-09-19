from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.provider_runtime import ProviderRateLimiter, with_retries
from app.public_contact_discovery import discover_public_phones
from app.settings import settings


@dataclass(frozen=True)
class ContactDiscoveryCandidate:
    name: str | None
    title: str | None
    email: str | None
    phone: str | None
    phone_type: str | None
    contact_type: str
    source_url: str
    verification_status: str
    verification_confidence: str | None


@dataclass(frozen=True)
class ContactDiscoveryContext:
    company_name: str
    company_domain: str
    source_urls: list[str]
    role_keywords: list[str]


class ContactProvider(Protocol):
    name: str
    async def discover(self, context: ContactDiscoveryContext) -> list[ContactDiscoveryCandidate]:
        ...


class OfficialWebsiteProvider:
    name = "official_website"

    def __init__(self) -> None:
        self.limiter = ProviderRateLimiter(settings.provider_requests_per_minute)

    async def discover(self, context: ContactDiscoveryContext) -> list[ContactDiscoveryCandidate]:
        await self.limiter.wait()
        phones = await discover_public_phones(source_urls=context.source_urls, allowed_domain=context.company_domain)
        return [
            ContactDiscoveryCandidate(
                name=None, title=None, email=None, phone=item.phone, phone_type="public_work_phone",
                contact_type="public_business_contact", source_url=item.source_url,
                verification_status="source_checked", verification_confidence="medium",
            )
            for item in phones
        ]


class HunterProvider:
    name = "hunter"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.hunter_api_key
        self.limiter = ProviderRateLimiter(settings.provider_requests_per_minute)

    async def discover(self, context: ContactDiscoveryContext) -> list[ContactDiscoveryCandidate]:
        if not self.api_key:
            return []

        async def request() -> dict:
            await self.limiter.wait()
            async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
                response = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={"domain": context.company_domain, "api_key": self.api_key, "limit": 50},
                )
                response.raise_for_status()
                return response.json()

        payload = await with_retries(request)
        domain = context.company_domain.lower().removeprefix("www.")
        results: list[ContactDiscoveryCandidate] = []
        for item in payload.get("data", {}).get("emails", []):
            email = str(item.get("value") or "").strip().lower()
            sources = item.get("sources") or []
            if not email or "@" not in email or not sources:
                continue
            source = sources[0] if isinstance(sources[0], dict) else {}
            source_url = source.get("uri")
            host = (urlsplit(source_url).hostname or "").lower().removeprefix("www.") if source_url else ""
            if not source_url or (host != domain and not host.endswith("." + domain)):
                continue
            name = " ".join(
                x for x in (str(item.get("first_name") or "").strip(), str(item.get("last_name") or "").strip()) if x
            ) or None
            title = str(item.get("position") or "").strip() or None
            confidence = item.get("confidence")
            results.append(
                ContactDiscoveryCandidate(
                    name=name, title=title, email=email, phone=None, phone_type=None,
                    contact_type="public_professional_email", source_url=source_url,
                    verification_status="source_checked",
                    verification_confidence=str(confidence) if confidence is not None else "medium",
                )
            )
        return results


class ContactProviderRegistry:
    def __init__(self, providers: list[ContactProvider] | None = None, include_optional: bool = True) -> None:
        if providers is not None:
            self._providers = providers
            return
        self._providers: list[ContactProvider] = [OfficialWebsiteProvider()]
        if include_optional and settings.hunter_api_key:
            self._providers.append(HunterProvider())

    def providers(self) -> tuple[ContactProvider, ...]:
        return tuple(self._providers)

    def add(self, provider: ContactProvider) -> None:
        self._providers.append(provider)
