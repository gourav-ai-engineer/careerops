from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.candidate_fit import VERIFIABLE_JOB_STATUSES
from app.database import get_db
from app.models import Job, JobFitAssessment
from app.settings import settings
from app.smartsheet_contact_sync import (
    ContactSyncOperation,
    apply_contact_sync_plan,
    build_contact_sync_plan,
)
from app.smartsheet_sync import SmartsheetClient, apply_job_sync_plan, build_job_sync_plan

router = APIRouter(prefix="/sync/smartsheet", tags=["smartsheet-sync"])


class SyncOperationResponse(BaseModel):
    action: str
    job_id: int
    reason: str
    row_id: int | None
    changed_cells: list[int]


class SyncPreviewResponse(BaseModel):
    sheet_id: int
    operations: list[SyncOperationResponse]
    adds: int
    updates: int


class SyncApplyRequest(BaseModel):
    job_ids: list[int] = Field(default_factory=list)


class SyncApplyResponse(BaseModel):
    sheet_id: int
    added: int
    updated: int
    unchanged: int


class ContactSyncOperationResponse(BaseModel):
    action: str
    job_id: int
    row_id: int | None
    reason: str
    changed_cells: list[int]


class ContactSyncPreviewResponse(BaseModel):
    sheet_id: int
    operations: list[ContactSyncOperationResponse]
    updates: int
    skipped: int
    unchanged: int


class ContactSyncApplyResponse(BaseModel):
    sheet_id: int
    updated: int
    skipped: int
    unchanged: int


def _load_jobs(db: Session, job_ids: list[int]) -> list[Job]:
    query = (
        select(Job)
        .options(selectinload(Job.company))
        .where(Job.status.in_(VERIFIABLE_JOB_STATUSES))
    )
    if job_ids:
        query = query.where(Job.id.in_(job_ids))
    return list(db.scalars(query.order_by(Job.first_seen_at.desc(), Job.id.desc())))


def _load_jobs_with_contacts(db: Session, job_ids: list[int]) -> list[Job]:
    query = (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.contacts).selectinload("contact"),
        )
        .where(Job.status.in_(VERIFIABLE_JOB_STATUSES))
    )
    if job_ids:
        query = query.where(Job.id.in_(job_ids))
    return list(db.scalars(query.order_by(Job.first_seen_at.desc(), Job.id.desc())))


def _fit_score_map(db: Session, job_ids: list[int]) -> dict[int, int]:
    query = select(JobFitAssessment).where(JobFitAssessment.candidate_profile_id == 1)
    if job_ids:
        query = query.where(JobFitAssessment.job_id.in_(job_ids))
    return {item.job_id: item.score for item in db.scalars(query)}


def _plan(db: Session, client: SmartsheetClient, job_ids: list[int]):
    sheet_id = settings.smartsheet_jobs_sheet_id
    if not sheet_id:
        raise HTTPException(status_code=500, detail="SMARTSHEET_JOBS_SHEET_ID is not configured")
    sheet = client.get_sheet(sheet_id)
    jobs = _load_jobs(db, job_ids)
    fit_scores = _fit_score_map(db, job_ids)
    return build_job_sync_plan(jobs, sheet, fit_scores)


def _contact_plan(db: Session, client: SmartsheetClient, job_ids: list[int]):
    sheet_id = settings.smartsheet_jobs_sheet_id
    if not sheet_id:
        raise HTTPException(status_code=500, detail="SMARTSHEET_JOBS_SHEET_ID is not configured")
    sheet = client.get_sheet(sheet_id)
    jobs = _load_jobs_with_contacts(db, job_ids)
    return build_contact_sync_plan(jobs, sheet)


@router.post("/dry-run", response_model=SyncPreviewResponse)
def dry_run_sync(job_ids: list[int] | None = None, db: Session = Depends(get_db)) -> SyncPreviewResponse:
    try:
        client = SmartsheetClient()
        plan = _plan(db, client, job_ids or [])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to read Smartsheet: {exc}") from exc

    operations = [
        SyncOperationResponse(
            action=operation.action,
            job_id=operation.job_id,
            reason=operation.reason,
            row_id=operation.row_id,
            changed_cells=[int(cell["columnId"]) for cell in operation.cells],
        )
        for operation in plan.operations
    ]
    return SyncPreviewResponse(
        sheet_id=plan.sheet_id,
        operations=operations,
        adds=sum(item.action == "add" for item in plan.operations),
        updates=sum(item.action == "update" for item in plan.operations),
    )


@router.post("/apply", response_model=SyncApplyResponse)
def apply_sync(payload: SyncApplyRequest, db: Session = Depends(get_db)) -> SyncApplyResponse:
    try:
        client = SmartsheetClient()
        plan = _plan(db, client, payload.job_ids)
        result = apply_job_sync_plan(client, plan)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Smartsheet synchronization failed: {exc}") from exc
    return SyncApplyResponse(sheet_id=plan.sheet_id, **result)


@router.post("/contacts/dry-run", response_model=ContactSyncPreviewResponse)
def dry_run_contact_sync(
    job_ids: list[int] | None = None,
    db: Session = Depends(get_db),
) -> ContactSyncPreviewResponse:
    try:
        client = SmartsheetClient()
        plan = _contact_plan(db, client, job_ids or [])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Unable to read Smartsheet: {exc}") from exc

    operations = [
        ContactSyncOperationResponse(
            action=operation.action,
            job_id=operation.job_id,
            row_id=operation.row_id,
            reason=operation.reason,
            changed_cells=[int(cell["columnId"]) for cell in operation.cells],
        )
        for operation in plan.operations
    ]
    return ContactSyncPreviewResponse(
        sheet_id=plan.sheet_id,
        operations=operations,
        updates=sum(item.action == "update" for item in plan.operations),
        skipped=sum(item.action == "skip" for item in plan.operations),
        unchanged=sum(item.action == "unchanged" for item in plan.operations),
    )


@router.post("/contacts/apply", response_model=ContactSyncApplyResponse)
def apply_contact_sync(
    payload: SyncApplyRequest,
    db: Session = Depends(get_db),
) -> ContactSyncApplyResponse:
    try:
        client = SmartsheetClient()
        plan = _contact_plan(db, client, payload.job_ids)
        result = apply_contact_sync_plan(client, plan)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Smartsheet contact synchronization failed: {exc}") from exc
    return ContactSyncApplyResponse(sheet_id=plan.sheet_id, **result)
