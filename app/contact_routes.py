from fastapi import APIRouter, Depends
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.contact_discovery import (
    PublicContactCandidate,
    normalize_phone,
    validate_public_contact,
)
from app.contact_service import upsert_public_contact
from app.database import get_db

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
    priority: str | None = None


class ContactUpsertResponse(BaseModel):
    id: int
    company_id: int
    created: bool
    verification_status: str | None


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
        from fastapi import HTTPException

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
