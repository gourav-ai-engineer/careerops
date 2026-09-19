from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Job, JobStatusHistory


ALLOWED_STATUSES = frozenset(
    {
        "discovered",
        "needs_review",
        "verified",
        "shortlisted",
        "applied",
        "interview",
        "offer",
        "rejected",
        "closed",
        "archived",
    }
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "discovered": frozenset({"needs_review", "verified", "rejected", "archived"}),
    "needs_review": frozenset({"discovered", "verified", "rejected", "archived"}),
    "verified": frozenset({"shortlisted", "applied", "rejected", "closed", "archived"}),
    "shortlisted": frozenset({"verified", "applied", "rejected", "archived"}),
    "applied": frozenset({"interview", "rejected", "offer", "closed"}),
    "interview": frozenset({"applied", "offer", "rejected", "closed"}),
    "offer": frozenset({"closed", "rejected"}),
    "rejected": frozenset({"discovered", "needs_review", "closed", "archived"}),
    "closed": frozenset({"discovered", "archived"}),
    "archived": frozenset({"discovered"}),
}


@dataclass(frozen=True)
class StatusChangeResult:
    job: Job
    history: JobStatusHistory


def validate_transition(current_status: str, next_status: str) -> None:
    if next_status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported status: {next_status}")
    if current_status not in ALLOWED_STATUSES:
        raise ValueError(f"Job has unsupported current status: {current_status}")
    if current_status == next_status:
        raise ValueError("Job is already in the requested status")
    if next_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(f"Invalid status transition: {current_status} -> {next_status}")


def change_job_status(
    db: Session,
    job: Job,
    next_status: str,
    reason: str | None = None,
) -> StatusChangeResult:
    next_status = next_status.strip().lower()
    validate_transition(job.status, next_status)

    previous_status = job.status
    job.status = next_status
    job.last_checked_at = datetime.now(timezone.utc)

    history = JobStatusHistory(
        job_id=job.id,
        from_status=previous_status,
        to_status=next_status,
        reason=reason.strip() if reason and reason.strip() else None,
    )
    db.add(history)
    db.commit()
    db.refresh(job)
    db.refresh(history)
    return StatusChangeResult(job=job, history=history)
