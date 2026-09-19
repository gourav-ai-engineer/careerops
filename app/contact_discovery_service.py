from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contact_discovery import PublicContactCandidate, normalize_phone, validate_public_contact
from app.contact_providers import ContactDiscoveryCandidate
from app.models import Company, Contact, ContactEvidence


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def normalize_email(value: str | None) -> str | None:
    normalized = normalize_text(value)
    return normalized.lower() if normalized else None


def normalize_company_name(value: str) -> str:
    return " ".join(value.lower().split()).strip()


def upsert_discovered_contact(
    db: Session,
    *,
    company_name: str,
    company_domain: str | None,
    candidate: ContactDiscoveryCandidate,
    provider: str,
) -> tuple[Contact, bool, ContactEvidence]:
    public_candidate = PublicContactCandidate(
        name=candidate.name,
        title=candidate.title,
        phone=normalize_phone(candidate.phone),
        phone_type=candidate.phone_type,
        source_url=candidate.source_url,
        verification_status=candidate.verification_status,
        verification_confidence=candidate.verification_confidence,
    )
    issues = validate_public_contact(public_candidate)
    if issues:
        raise ValueError("; ".join(issues))

    normalized_company = normalize_company_name(company_name)
    company = db.scalar(select(Company).where(Company.normalized_name == normalized_company))
    if company is None:
        company = Company(
            name=company_name.strip(),
            normalized_name=normalized_company,
            domain=normalize_text(company_domain),
        )
        db.add(company)
        db.flush()
    elif company_domain and not company.domain:
        company.domain = normalize_text(company_domain)

    normalized_email = normalize_email(candidate.email)
    contact = None
    if normalized_email:
        contact = db.scalar(select(Contact).where(Contact.normalized_email == normalized_email))

    if contact is None and candidate.phone:
        contact = db.scalar(
            select(Contact).where(
                Contact.company_id == company.id,
                Contact.phone == normalize_phone(candidate.phone),
                Contact.source_url == candidate.source_url,
            )
        )

    created = contact is None
    if contact is None:
        contact = Contact(company_id=company.id)
        db.add(contact)

    contact.company_id = company.id
    contact.name = normalize_text(candidate.name)
    contact.title = normalize_text(candidate.title)
    contact.email = normalize_text(candidate.email)
    contact.normalized_email = normalized_email
    contact.phone = normalize_phone(candidate.phone)
    contact.phone_type = normalize_text(candidate.phone_type)
    contact.contact_type = normalize_text(candidate.contact_type)
    contact.source_url = candidate.source_url
    contact.verification_status = candidate.verification_status
    contact.verification_confidence = normalize_text(candidate.verification_confidence)
    contact.verification_date = datetime.now(timezone.utc)

    db.flush()
    evidence = ContactEvidence(
        contact_id=contact.id,
        provider=provider,
        source_url=candidate.source_url,
        verification_status=candidate.verification_status,
        confidence=normalize_text(candidate.verification_confidence),
        reason="Discovered from a public source on the configured company domain.",
    )
    db.add(evidence)
    db.commit()
    db.refresh(contact)
    db.refresh(evidence)
    return contact, created, evidence
