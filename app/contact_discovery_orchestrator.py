from __future__ import annotations

from dataclasses import dataclass

from app.contact_discovery_service import upsert_discovered_contact
from app.contact_providers import ContactDiscoveryContext, ContactProviderRegistry
from app.models import Contact, Job


@dataclass(frozen=True)
class DiscoveryItem:
    provider: str
    contact: Contact
    created: bool


async def discover_and_persist_contacts(
    db,
    *,
    company_name: str,
    company_domain: str,
    source_urls: list[str],
    role_keywords: list[str] | None = None,
    registry: ContactProviderRegistry | None = None,
    job: Job | None = None,
) -> list[DiscoveryItem]:
    registry = registry or ContactProviderRegistry()
    context = ContactDiscoveryContext(
        company_name=company_name,
        company_domain=company_domain,
        source_urls=source_urls,
        role_keywords=role_keywords or [],
    )
    results: list[DiscoveryItem] = []

    for provider in registry.providers():
        candidates = await provider.discover(context)
        for candidate in candidates:
            contact, created, _ = upsert_discovered_contact(
                db,
                company_name=company_name,
                company_domain=company_domain,
                candidate=candidate,
                provider=provider.name,
            )
            if job is not None:
                existing_link = next(
                    (link for link in job.contacts if link.contact_id == contact.id),
                    None,
                )
                if existing_link is None:
                    from app.models import JobContact

                    job_link = JobContact(
                        job_id=job.id,
                        contact_id=contact.id,
                        relevance_reason="Discovered by configured public-contact provider for this job.",
                    )
                    db.add(job_link)
                    db.commit()
            results.append(DiscoveryItem(provider=provider.name, contact=contact, created=created))

    return results
