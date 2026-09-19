from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.live_verification import check_official_source
from app.models import Job, JobSourceEvidence

router = APIRouter(prefix="/jobs", tags=["live-verification"])


class LiveVerificationResponse(BaseModel):
    status: str
    requested_url: str
    final_url: str | None
    http_status: int | None
    title: str | None
    reason: str


@router.post("/{job_id}/verify-live", response_model=LiveVerificationResponse)
async def verify_live(job_id: int, db: Session = Depends(get_db)) -> LiveVerificationResponse:
    job = db.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.application_url:
        raise HTTPException(status_code=409, detail="Job has no application URL")
    if not job.company.domain:
        raise HTTPException(status_code=409, detail="Company has no stored domain")
    result = await check_official_source(job.application_url, job.company.domain)
    db.add(JobSourceEvidence(
        job_id=job.id, source_url=job.application_url, source_type="live_official_source_check",
        verification_status=result.status, verification_reason=result.reason,
    ))
    db.commit()
    return LiveVerificationResponse(**result.__dict__)
