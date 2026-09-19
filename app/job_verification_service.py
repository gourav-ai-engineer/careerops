from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.job_status import change_job_status
from app.job_verification import verify_job_source
from app.official_verification import verify_official_domain
from app.models import Job, JobSourceEvidence


@dataclass(frozen=True)
class VerificationOutcome:
    status: str
    reason: str
    evidence: JobSourceEvidence
    previous_status: str
    current_status: str


def verify_and_record(
    db: Session,
    job: Job,
    *,
    decision: str,
    reason: str | None = None,
) -> VerificationOutcome:
    decision = decision.strip().lower()
    if decision not in {"verified", "rejected"}:
        raise ValueError("Verification decision must be verified or rejected")

    candidate_url = job.application_url or job.source_url
    if not candidate_url:
        raise ValueError("Job has no application_url or source_url to verify")

    source_type = "application" if job.application_url else "source"
    screened = verify_job_source(candidate_url, candidate_url, job.company.domain)
    official = verify_official_domain(job.application_url, job.company.domain)

    if decision == "verified" and official.status != "screened":
        raise ValueError(
            "Job cannot be verified until the application host matches the stored company domain"
        )

    evidence_reason = reason.strip() if reason and reason.strip() else (
        "Operator confirmed the job after official-domain screening"
        if decision == "verified"
        else "Operator rejected the job during verification review"
    )

    evidence = JobSourceEvidence(
        job_id=job.id,
        source_url=candidate_url,
        source_type=source_type,
        verification_status=decision,
        verification_reason=(
            f"{evidence_reason}. Screening: {screened.reason}. Official-domain check: {official.reason}"
        ),
    )
    db.add(evidence)
    db.flush()

    previous_status = job.status
    status_result = change_job_status(db, job, decision, evidence_reason)

    return VerificationOutcome(
        status=decision,
        reason=status_result.history.reason or evidence_reason,
        evidence=evidence,
        previous_status=previous_status,
        current_status=status_result.job.status,
    )
