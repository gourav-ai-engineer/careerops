from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Contact, Job, JobFitAssessment, ProcessingRun

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)) -> dict:
    total_jobs = db.scalar(select(func.count()).select_from(Job)) or 0
    total_contacts = db.scalar(select(func.count()).select_from(Contact)) or 0
    total_runs = db.scalar(select(func.count()).select_from(ProcessingRun)) or 0
    status_counts = Counter(db.scalars(select(Job.status)))
    verified_contacts = db.scalar(select(func.count()).select_from(Contact).where(Contact.verification_status == "verified")) or 0
    source_checked_contacts = db.scalar(select(func.count()).select_from(Contact).where(Contact.verification_status == "source_checked")) or 0
    scores = list(db.scalars(select(JobFitAssessment.score)))
    avg_fit = round(sum(scores) / len(scores), 1) if scores else None
    recent_jobs = list(db.scalars(select(Job).options(selectinload(Job.company)).order_by(Job.first_seen_at.desc(), Job.id.desc()).limit(8)))
    recent_runs = list(db.scalars(select(ProcessingRun).order_by(ProcessingRun.started_at.desc(), ProcessingRun.id.desc()).limit(5)))
    return {
        "jobs": {"total": total_jobs, "by_status": dict(status_counts)},
        "contacts": {"total": total_contacts, "verified": verified_contacts, "source_checked": source_checked_contacts},
        "fit": {"average_score": avg_fit},
        "runs": {"total": total_runs},
        "recent_jobs": [
            {"id": job.id, "company": job.company.name, "title": job.title, "location": job.location, "status": job.status, "application_url": job.application_url}
            for job in recent_jobs
        ],
        "recent_runs": [
            {"id": run.id, "run_type": run.run_type, "status": run.status, "output_count": run.output_count, "error_count": run.error_count, "started_at": run.started_at}
            for run in recent_runs
        ],
    }
