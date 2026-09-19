import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contact_discovery import (
    PublicContactCandidate,
    normalize_phone,
    validate_public_contact,
)
from app.contact_discovery_orchestrator import discover_and_persist_contacts
from app.contact_service import upsert_public_contact
from app.contact_providers import ContactProviderRegistry
from app.database import get_db
from app.models import Job
from app.public_contact_discovery import PublicPhoneCandidate, discover_public_phones

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactValidationRequest(BaseModel):
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    phone_type: str | None = None
    source_url: HttpUrl
    verification_status: str = "unverified"
    verification_confidence: str | None = None


class ContactValidationResponse(BaseModel):
    valid: bool
    normalized_phone: str | None
    issues: list[str]


class ContactUpsertRequest(ContactValidationRequest):
    company_name: str
    company_domain: str | None = None
    email: str | None = None
    contact_type: str | None = None
    linkedin_url: HttpUrl | None = None
    priority: str | None = None


class ContactUpsertResponse(BaseModel):
    id: int
    company_id: int
    created: bool
    verification_status: str | None


class PublicPhoneDiscoveryRequest(BaseModel):
    source_urls: list[HttpUrl]
    allowed_domain: str


class PublicPhoneDiscoveryResponse(BaseModel):
    candidates: list[PublicPhoneCandidate]


class ContactDiscoveryRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    company_domain: str = Field(min_length=1, max_length=255)
    source_urls: list[HttpUrl] = Field(min_length=1, max_length=20)
    role_keywords: list[str] = Field(default_factory=list)
    job_id: int | None = Field(default=None, ge=1)


class DiscoveredContactResponse(BaseModel):
    id: int
    company_id: int
    provider: str
    created: bool
    phone: str | None
    phone_type: str | None
    source_url: str
    verification_status: str | None
    verification_confidence: str | None


class ContactDiscoveryResponse(BaseModel):
    providers: list[str]
    discovered: int
    created: int
    items: list[DiscoveredContactResponse]


@router.post("/validate", response_model=ContactValidationResponse)
def validate_contact(payload: ContactValidationRequest) -> ContactValidationResponse:
    candidate = PublicContactCandidate(
        name=payload.name,
        title=payload.title,
        phone=normalize_phone(payload.phone),
        phone_type=payload.phone_type,
        source_url=str(payload.source_url),
        verification_status=payload.verification_status,
        verification_confidence=payload.verification_confidence,
    )
    issues = validate_public_contact(candidate)
    return ContactValidationResponse(
        valid=not issues,
        normalized_phone=candidate.phone,
        issues=issues,
    )


@router.post("", response_model=ContactUpsertResponse, status_code=201)
def create_or_update_contact(
    payload: ContactUpsertRequest,
    db: Session = Depends(get_db),
) -> ContactUpsertResponse:
    candidate = PublicContactCandidate(
        name=payload.name,
        title=payload.title,
        phone=normalize_phone(payload.phone),
        phone_type=payload.phone_type,
        source_url=str(payload.source_url),
        verification_status=payload.verification_status,
        verification_confidence=payload.verification_confidence,
    )
    issues = validate_public_contact(candidate)
    if issues:
        raise HTTPException(status_code=422, detail=issues)

    contact, created = upsert_public_contact(
        db,
        company_name=payload.company_name,
        company_domain=payload.company_domain,
        name=payload.name,
        title=payload.title,
        email=payload.email,
        phone=candidate.phone,
        phone_type=payload.phone_type,
        contact_type=payload.contact_type,
        linkedin_url=str(payload.linkedin_url) if payload.linkedin_url else None,
        source_url=str(payload.source_url),
        verification_status=payload.verification_status,
        verification_confidence=payload.verification_confidence,
        priority=payload.priority,
    )
    return ContactUpsertResponse(
        id=contact.id,
        company_id=contact.company_id,
        created=created,
        verification_status=contact.verification_status,
    )


@router.post("/discover-public", response_model=PublicPhoneDiscoveryResponse)
async def discover_public_contact_phones(
    payload: PublicPhoneDiscoveryRequest,
) -> PublicPhoneDiscoveryResponse:
    try:
        candidates = await discover_public_phones(
            source_urls=[str(url) for url in payload.source_urls],
            allowed_domain=payload.allowed_domain,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PublicPhoneDiscoveryResponse(candidates=candidates)


@router.post("/discover", response_model=ContactDiscoveryResponse)
async def discover_contacts(
    payload: ContactDiscoveryRequest,
    db: Session = Depends(get_db),
) -> ContactDiscoveryResponse:
    job = None
    if payload.job_id is not None:
        job = db.scalar(select(Job).where(Job.id == payload.job_id))
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.company.domain and job.company.domain.lower() != payload.company_domain.lower().removeprefix("www."):
            raise HTTPException(
                status_code=409,
                detail="Discovery domain does not match the job's stored company domain",
            )

    registry = ContactProviderRegistry()
    try:
        items = await discover_and_persist_contacts(
            db,
            company_name=payload.company_name,
            company_domain=payload.company_domain,
            source_urls=[str(url) for url in payload.source_urls],
            role_keywords=payload.role_keywords,
            registry=registry,
            job=job,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ContactDiscoveryResponse(
        providers=[provider.name for provider in registry.providers()],
        discovered=len(items),
        created=sum(item.created for item in items),
        items=[
            DiscoveredContactResponse(
                id=item.contact.id,
                company_id=item.contact.company_id,
                provider=item.provider,
                created=item.created,
                phone=item.contact.phone,
                phone_type=item.contact.phone_type,
                source_url=item.contact.source_url or "",
                verification_status=item.contact.verification_status,
                verification_confidence=item.contact.verification_confidence,
            )
            for item in items
        ],
    )
