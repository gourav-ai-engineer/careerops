import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.audit import record_audit
from app.database import get_db
from app.models import Job, ResumeDraft
from app.resume_engine import create_resume_draft, get_master_resume, save_master_resume

router = APIRouter(prefix="/resume", tags=["resume"])


class MasterResumeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class MasterResumeResponse(BaseModel):
    id: int
    name: str
    version: int
    content: str


class ResumeDraftResponse(BaseModel):
    id: int
    job_id: int
    status: str
    content: str
    change_plan: list[str]
    matched_keywords: list[str]
    missing_keywords: list[str]
    created_at: datetime | None
    approved_at: datetime | None
    job_title: str
    company_name: str


class DraftStatusRequest(BaseModel):
    status: str


@router.get("/master", response_model=MasterResumeResponse | None)
def get_master(db: Session = Depends(get_db)) -> MasterResumeResponse | None:
    item = get_master_resume(db)
    if item is None:
        return None
    return MasterResumeResponse(id=item.id, name=item.name, version=item.version, content=item.content)


@router.put("/master", response_model=MasterResumeResponse)
def put_master(payload: MasterResumeRequest, db: Session = Depends(get_db)) -> MasterResumeResponse:
    item = save_master_resume(db, name=payload.name, content=payload.content)
    record_audit(db, entity_type="resume", entity_id=item.id, action="master_saved")
    return MasterResumeResponse(id=item.id, name=item.name, version=item.version, content=item.content)


@router.post("/drafts/{job_id}", response_model=ResumeDraftResponse, status_code=201)
def generate_draft(job_id: int, db: Session = Depends(get_db)) -> ResumeDraftResponse:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        draft = create_resume_draft(db, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(db, entity_type="resume_draft", entity_id=draft.id, action="draft_generated", metadata={"job_id": job_id})
    draft = db.scalar(select(ResumeDraft).options(selectinload(ResumeDraft.job).selectinload(Job.company)).where(ResumeDraft.id == draft.id))
    return _draft_response(draft)


@router.get("/drafts", response_model=list[ResumeDraftResponse])
def list_drafts(status: str | None = None, limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)) -> list[ResumeDraftResponse]:
    statement = select(ResumeDraft).options(selectinload(ResumeDraft.job).selectinload(Job.company))
    if status:
        statement = statement.where(ResumeDraft.status == status)
    drafts = list(db.scalars(statement.order_by(ResumeDraft.created_at.desc()).limit(limit)))
    return [_draft_response(item) for item in drafts]


@router.patch("/drafts/{draft_id}", response_model=ResumeDraftResponse)
def update_draft_status(draft_id: int, payload: DraftStatusRequest, db: Session = Depends(get_db)) -> ResumeDraftResponse:
    if payload.status not in {"draft", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="status must be draft, approved, or rejected")
    draft = db.scalar(select(ResumeDraft).options(selectinload(ResumeDraft.job).selectinload(Job.company)).where(ResumeDraft.id == draft_id))
    if draft is None:
        raise HTTPException(status_code=404, detail="Resume draft not found")
    draft.status = payload.status
    draft.approved_at = datetime.now(timezone.utc) if payload.status == "approved" else None
    db.commit()
    db.refresh(draft)
    record_audit(db, entity_type="resume_draft", entity_id=draft.id, action=f"draft_{payload.status}")
    return _draft_response(draft)


def _draft_response(draft: ResumeDraft) -> ResumeDraftResponse:
    return ResumeDraftResponse(
        id=draft.id, job_id=draft.job_id, status=draft.status, content=draft.content,
        change_plan=json.loads(draft.change_plan), matched_keywords=json.loads(draft.matched_keywords),
        missing_keywords=json.loads(draft.missing_keywords), created_at=draft.created_at,
        approved_at=draft.approved_at, job_title=draft.job.title, company_name=draft.job.company.name,
    )
