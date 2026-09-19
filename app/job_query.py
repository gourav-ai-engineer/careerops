from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Company, Job


@dataclass(frozen=True)
class JobSearchResult:
    items: list[Job]
    total: int
    page: int
    page_size: int


def search_jobs(
    db: Session,
    *,
    company: str | None = None,
    title: str | None = None,
    status: str | None = None,
    role_family: str | None = None,
    location: str | None = None,
    priority: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> JobSearchResult:
    filters = []
    if company:
        filters.append(Company.name.ilike(f"%{company.strip()}%"))
    if title:
        filters.append(Job.title.ilike(f"%{title.strip()}%"))
    if status:
        filters.append(Job.status == status.strip())
    if role_family:
        filters.append(Job.role_family == role_family.strip())
    if location:
        filters.append(Job.location.ilike(f"%{location.strip()}%"))
    if priority:
        filters.append(Job.priority == priority.strip())

    base = select(Job).join(Company).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = list(
        db.scalars(
            base.order_by(Job.first_seen_at.desc(), Job.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return JobSearchResult(items=items, total=total, page=page, page_size=page_size)
