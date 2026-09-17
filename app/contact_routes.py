from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from app.contact_discovery import PublicContactCandidate, normalize_phone, validate_public_contact

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
