from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact, ContactEvidence, JobContact


@dataclass(frozen=True)
class ContactDuplicate:
    primary_id: int
    duplicate_id: int
    reason: str


def find_duplicate_contacts(db: Session) -> list[ContactDuplicate]:
    contacts = list(db.scalars(select(Contact).order_by(Contact.company_id, Contact.id)))
    results: list[ContactDuplicate] = []
    seen_email: dict[str, int] = {}
    seen_phone: dict[tuple[int, str], int] = {}
    seen_linkedin: dict[str, int] = {}
    for contact in contacts:
        if contact.normalized_email:
            primary = seen_email.setdefault(contact.normalized_email, contact.id)
            if primary != contact.id:
                results.append(ContactDuplicate(primary, contact.id, "same normalized email"))
                continue
        if contact.phone and contact.company_id:
            key = (contact.company_id, " ".join(contact.phone.split()))
            primary = seen_phone.setdefault(key, contact.id)
            if primary != contact.id:
                results.append(ContactDuplicate(primary, contact.id, "same company and phone"))
                continue
        if contact.linkedin_url:
            key = contact.linkedin_url.rstrip("/").lower()
            primary = seen_linkedin.setdefault(key, contact.id)
            if primary != contact.id:
                results.append(ContactDuplicate(primary, contact.id, "same LinkedIn URL"))
    return results


def merge_contacts(db: Session, primary_id: int, duplicate_id: int) -> Contact:
    if primary_id == duplicate_id:
        raise ValueError("Primary and duplicate contact must differ")
    primary = db.scalar(select(Contact).where(Contact.id == primary_id))
    duplicate = db.scalar(select(Contact).where(Contact.id == duplicate_id))
    if primary is None or duplicate is None:
        raise ValueError("Both contacts must exist")
    if primary.company_id != duplicate.company_id:
        raise ValueError("Contacts must belong to the same company")
    for field in (
        "name", "title", "email", "normalized_email", "phone", "phone_type",
        "contact_type", "linkedin_url", "source_url", "verification_status",
        "verification_confidence", "verification_date", "priority",
    ):
        if getattr(primary, field) in (None, "") and getattr(duplicate, field) not in (None, ""):
            setattr(primary, field, getattr(duplicate, field))

    links = list(db.scalars(select(JobContact).where(JobContact.contact_id == duplicate_id)))
    for link in links:
        existing = db.get(JobContact, {"job_id": link.job_id, "contact_id": primary_id})
        if existing is None:
            link.contact_id = primary_id
        else:
            db.delete(link)
    evidence = list(db.scalars(select(ContactEvidence).where(ContactEvidence.contact_id == duplicate_id)))
    for item in evidence:
        item.contact_id = primary_id
    db.delete(duplicate)
    db.commit()
    db.refresh(primary)
    return primary
