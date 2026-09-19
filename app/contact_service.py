from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Contact


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


def upsert_public_contact(
    db: Session,
    *,
    company_name: str,
    company_domain: str | None,
    name: str | None,
    title: str | None,
    email: str | None,
    phone: str | None,
    phone_type: str | None,
    contact_type: str | None,
    linkedin_url: str | None,
    source_url: str,
    verification_status: str,
    verification_confidence: str | None,
    priority: str | None,
) -> tuple[Contact, bool]:
    normalized_company = normalize_company_name(company_name)
    company = db.scalar(
        select(Company).where(Company.normalized_name == normalized_company)
    )
    if company is None:
        company = Company(
            name=company_name.strip(),
            normalized_name=normalized_company,
            domain=normalize_text(company_domain),
        )
        db.add(company)
        db.flush()

    normalized_email = normalize_email(email)
    contact = None
    if normalized_email:
        contact = db.scalar(
            select(Contact).where(Contact.normalized_email == normalized_email)
        )

    if contact is None and phone:
        contact = db.scalar(
            select(Contact).where(
                Contact.company_id == company.id,
                Contact.phone == normalize_text(phone),
                Contact.source_url == source_url,
            )
        )

    created = contact is None
    if contact is None:
        contact = Contact(company_id=company.id)
        db.add(contact)

    contact.company_id = company.id
    contact.name = normalize_text(name)
    contact.title = normalize_text(title)
    contact.email = normalize_text(email)
    contact.normalized_email = normalized_email
    contact.phone = normalize_text(phone)
    contact.phone_type = normalize_text(phone_type)
    contact.contact_type = normalize_text(contact_type)
    contact.linkedin_url = normalize_text(linkedin_url)
    contact.source_url = source_url
    contact.verification_status = verification_status
    contact.verification_confidence = normalize_text(verification_confidence)
    contact.verification_date = datetime.now(timezone.utc)
    contact.priority = normalize_text(priority)

    db.commit()
    db.refresh(contact)
    return contact, created
