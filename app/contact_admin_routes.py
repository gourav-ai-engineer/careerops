from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.contact_quality import find_duplicate_contacts, merge_contacts
from app.database import get_db
from app.models import Company, Contact

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactListItem(BaseModel):
    id: int
    company_id: int
    company_name: str
    name: str | None
    title: str | None
    email: str | None
    phone: str | None
    phone_type: str | None
    linkedin_url: HttpUrl | None
    source_url: HttpUrl | None
    verification_status: str | None
    verification_confidence: str | None
    priority: str | None


class ContactListResponse(BaseModel):
    items: list[ContactListItem]
    total: int
    page: int
    page_size: int


class MergeContactsRequest(BaseModel):
    primary_id: int
    duplicate_id: int


@router.get("/list", response_model=ContactListResponse)
def list_contacts(company: str | None = None, verification_status: str | None = None,
                  email_only: bool = False, page: int = Query(default=1, ge=1),
                  page_size: int = Query(default=25, ge=1, le=100),
                  db: Session = Depends(get_db)) -> ContactListResponse:
    filters = []
    if company:
        filters.append(Company.name.ilike(f"%{company.strip()}%"))
    if verification_status:
        filters.append(Contact.verification_status == verification_status.strip())
    if email_only:
        filters.append(Contact.email.is_not(None))
    base = select(Contact).join(Company).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    contacts = list(
        db.scalars(
            base.options(selectinload(Contact.company))
            .order_by(Contact.priority.desc().nullslast(), Contact.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    )
    return ContactListResponse(
        items=[
            ContactListItem(
                id=item.id, company_id=item.company_id, company_name=item.company.name,
                name=item.name, title=item.title, email=item.email, phone=item.phone,
                phone_type=item.phone_type, linkedin_url=item.linkedin_url,
                source_url=item.source_url, verification_status=item.verification_status,
                verification_confidence=item.verification_confidence, priority=item.priority,
            ) for item in contacts
        ], total=total, page=page, page_size=page_size,
    )


@router.get("/duplicates")
def duplicates(db: Session = Depends(get_db)) -> list[dict]:
    return [{"primary_id": x.primary_id, "duplicate_id": x.duplicate_id, "reason": x.reason} for x in find_duplicate_contacts(db)]


@router.post("/merge")
def merge(payload: MergeContactsRequest, db: Session = Depends(get_db)) -> dict:
    try:
        contact = merge_contacts(db, payload.primary_id, payload.duplicate_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id": contact.id, "merged_duplicate_id": payload.duplicate_id}
