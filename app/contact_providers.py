from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.public_contact_discovery import discover_public_phones


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

    async def discover(
        self,
        context: ContactDiscoveryContext,
    ) -> list[ContactDiscoveryCandidate]:
        ...


class OfficialWebsiteProvider:
    """Provider for public business contact details published on the employer domain."""

    name = "official_website"

    async def discover(
        self,
        context: ContactDiscoveryContext,
    ) -> list[ContactDiscoveryCandidate]:
        phones = await discover_public_phones(
            source_urls=context.source_urls,
            allowed_domain=context.company_domain,
        )
        return [
            ContactDiscoveryCandidate(
                name=None,
                title=None,
                email=None,
                phone=item.phone,
                phone_type="public_work_phone",
                contact_type="public_business_contact",
                source_url=item.source_url,
                verification_status="source_checked",
                verification_confidence="medium",
            )
            for item in phones
        ]


class ContactProviderRegistry:
    def __init__(self, providers: list[ContactProvider] | None = None) -> None:
        self._providers = providers or [OfficialWebsiteProvider()]

    def providers(self) -> tuple[ContactProvider, ...]:
        return tuple(self._providers)

    def add(self, provider: ContactProvider) -> None:
        self._providers.append(provider)
