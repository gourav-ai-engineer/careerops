import pytest

from app.contact_providers import ContactDiscoveryContext, ContactDiscoveryCandidate, ContactProviderRegistry


class FakeProvider:
    name = "fake"

    async def discover(self, context: ContactDiscoveryContext) -> list[ContactDiscoveryCandidate]:
        return []


def test_registry_has_official_website_provider() -> None:
    registry = ContactProviderRegistry()
    assert [provider.name for provider in registry.providers()] == ["official_website"]


def test_registry_accepts_additional_provider() -> None:
    registry = ContactProviderRegistry()
    registry.add(FakeProvider())
    assert [provider.name for provider in registry.providers()] == ["official_website", "fake"]


def test_discovery_context_is_explicit() -> None:
    context = ContactDiscoveryContext(
        company_name="Example",
        company_domain="example.com",
        source_urls=["https://example.com/careers"],
        role_keywords=["recruiting", "campus"],
    )
    assert context.company_domain == "example.com"
    assert context.role_keywords == ["recruiting", "campus"]


@pytest.mark.asyncio
async def test_fake_provider_contract() -> None:
    provider = FakeProvider()
    result = await provider.discover(
        ContactDiscoveryContext(
            company_name="Example",
            company_domain="example.com",
            source_urls=[],
            role_keywords=[],
        )
    )
    assert result == []
