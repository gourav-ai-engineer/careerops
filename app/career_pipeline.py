from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.candidate_fit import VERIFIABLE_JOB_STATUSES, assess_candidate_fit, persist_fit_assessment
from app.candidate_profile_store import CandidateProfileStore
from app.contact_discovery_orchestrator import discover_and_persist_contacts
from app.job_status import change_job_status
from app.job_verification import verify_job_source
from app.models import Job, JobFitAssessment, JobSourceEvidence, JobStatusHistory
from app.official_verification import verify_official_domain
from app.pipeline_ingestion import PipelineItem, process_text
from app.resume_engine import create_resume_draft, get_master_resume
from app.run_service import finish_run, start_run
from app.smartsheet_sync import SmartsheetClient, build_job_sync_plan


@dataclass
class StageResult:
    status: str
    reason: str


@dataclass
class PipelineRunItem:
    job_id: int
    company_name: str
    title: str
    ingestion: StageResult
    screening: StageResult
    live_check: StageResult
    fit: StageResult
    contacts: StageResult
    resume: StageResult
    smartsheet: StageResult
    required_action: str | None = None


@dataclass
class CareerPipelineResult:
    run_id: int
    processed: int
    items: list[PipelineRunItem]
    warnings: list[str] = field(default_factory=list)


def _job(db: Session, job_id: int) -> Job:
    item = db.scalar(
        select(Job)
        .options(selectinload(Job.company), selectinload(Job.requirements))
        .where(Job.id == job_id)
    )
    if item is None:
        raise ValueError(f"Job {job_id} disappeared during pipeline execution")
    return item


def _record_screening(db: Session, job: Job) -> StageResult:
    candidate = verify_job_source(job.application_url, job.source_url, job.company.domain)
    official = verify_official_domain(job.application_url, job.company.domain)
    reason = f"Source screening: {candidate.reason}. Official-domain screening: {official.reason}."
    evidence = db.scalar(
        select(JobSourceEvidence).where(
            JobSourceEvidence.job_id == job.id,
            JobSourceEvidence.source_url == (job.application_url or job.source_url),
            JobSourceEvidence.source_type == "initial_screening",
            JobSourceEvidence.verification_status == candidate.status,
        )
    )
    if evidence is None and (job.application_url or job.source_url):
        db.add(
            JobSourceEvidence(
                job_id=job.id,
                source_url=job.application_url or job.source_url,
                source_type="initial_screening",
                verification_status=candidate.status,
                verification_reason=reason,
            )
        )
        db.commit()

    # Screening only moves the record into review; it never auto-verifies a job.
    if job.status == "discovered":
        try:
            change_job_status(db, job, "needs_review", reason)
        except ValueError:
            pass

    return StageResult(candidate.status, reason)


async def run_career_pipeline(
    db: Session,
    *,
    text: str,
    live_check: bool = False,
    discover_contacts: bool = False,
    smartsheet_dry_run: bool = False,
    generate_resume_drafts: bool = False,
) -> CareerPipelineResult:
    run = start_run(db, "career_pipeline")
    results: list[PipelineRunItem] = []
    warnings: list[str] = []

    try:
        extraction = process_text(db, text)
        warnings.extend([])

        profile_store = CandidateProfileStore()
        profile = profile_store.load(db)

        for item in extraction:
            job = _job(db, item.job_id)
            ingestion = StageResult("duplicate" if item.duplicate else "persisted", item.reason)
            screening = _record_screening(db, job)

            live = StageResult("skipped", "Live check not requested")
            if live_check:
                if not job.application_url or not job.company.domain:
                    live = StageResult("needs_review", "Live check requires an application URL and stored company domain")
                else:
                    from app.live_verification import check_official_source
                    try:
                        check = await check_official_source(job.application_url, job.company.domain)
                        live = StageResult(check.status, check.reason)
                    except Exception as exc:
                        live = StageResult("error", f"Live source check failed: {exc}")

            fit = StageResult("skipped", "Job is not verified yet")
            if job.status in VERIFIABLE_JOB_STATUSES and profile:
                assessment: JobFitAssessment = persist_fit_assessment(
                    db, job, select_profile_record(db, profile.name), assess_candidate_fit(job, profile)
                )
                fit = StageResult("assessed", f"Fit score persisted: {assessment.score}/100")

            contacts = StageResult("skipped", "Contact discovery is gated on explicit job verification")
            if discover_contacts:
                if job.status not in VERIFIABLE_JOB_STATUSES:
                    contacts = StageResult("blocked", "Verify the job explicitly before contact discovery")
                elif not job.company.domain:
                    contacts = StageResult("needs_review", "Company domain is missing")
                else:
                    try:
                        items = await discover_and_persist_contacts(
                            db,
                            company_name=job.company.name,
                            company_domain=job.company.domain,
                            source_urls=[u for u in [job.application_url, job.source_url] if u],
                            role_keywords=[job.role_family] if job.role_family else [],
                            job=job,
                        )
                        contacts = StageResult("completed", f"Processed {len(items)} provider contact results")
                    except Exception as exc:
                        contacts = StageResult("error", f"Contact discovery failed: {exc}")

            resume = StageResult("skipped", "Resume draft generation is disabled")
            if generate_resume_drafts:
                if job.status not in VERIFIABLE_JOB_STATUSES:
                    resume = StageResult("blocked", "Verify the job before generating a job-specific resume draft")
                elif get_master_resume(db) is None:
                    resume = StageResult("needs_review", "Master resume is not configured")
                else:
                    try:
                        draft = create_resume_draft(db, job.id)
                        resume = StageResult("completed", f"Draft {draft.id} is available for review")
                    except Exception as exc:
                        resume = StageResult("error", f"Resume draft generation failed: {exc}")

            smartsheet = StageResult("skipped", "Smartsheet dry-run is disabled")
            if smartsheet_dry_run:
                if job.status not in VERIFIABLE_JOB_STATUSES:
                    smartsheet = StageResult("blocked", "Only verified/later-stage jobs are synchronized")
                elif not settings_ready_for_smartsheet():
                    smartsheet = StageResult("needs_review", "Smartsheet credentials are not configured")
                else:
                    try:
                        client = SmartsheetClient()
                        sheet_id = client.access_sheet_id
                        if sheet_id is None:
                            raise ValueError("SMARTSHEET_JOBS_SHEET_ID is not configured")
                        sheet = client.get_sheet(sheet_id)
                        fit_scores = {
                            a.job_id: a.score for a in db.scalars(
                                select(JobFitAssessment).where(JobFitAssessment.candidate_profile_id == 1)
                            )
                        }
                        plan = build_job_sync_plan([job], sheet, fit_scores)
                        smartsheet = StageResult("planned", f"{len(plan.operations)} Smartsheet operations planned")
                    except Exception as exc:
                        smartsheet = StageResult("error", f"Smartsheet dry-run failed: {exc}")

            action = None
            if job.status not in VERIFIABLE_JOB_STATUSES:
                action = "Explicitly verify this job after reviewing the source evidence."
            elif fit.status == "skipped" and profile is None:
                action = "Save a candidate profile before fit assessment."
            results.append(
                PipelineRunItem(
                    job_id=job.id,
                    company_name=job.company.name,
                    title=job.title,
                    ingestion=ingestion,
                    screening=screening,
                    live_check=live,
                    fit=fit,
                    contacts=contacts,
                    resume=resume,
                    smartsheet=smartsheet,
                    required_action=action,
                )
            )

        finish_run(
            db, run, status="succeeded", input_count=1, output_count=len(results),
            summary={"processed": len(results), "warnings": len(warnings)},
        )
        return CareerPipelineResult(run_id=run.id, processed=len(results), items=results, warnings=warnings)
    except Exception as exc:
        finish_run(db, run, status="failed", error_count=1, error_message=str(exc))
        raise


def select_profile_record(db: Session, name: str):
    from app.models import CandidateProfileRecord
    record = db.scalar(select(CandidateProfileRecord).where(CandidateProfileRecord.id == 1))
    if record is None:
        raise ValueError(f"Candidate profile {name} is not persisted")
    return record


def settings_ready_for_smartsheet() -> bool:
    from app.settings import settings
    return bool(settings.smartsheet_access_token and settings.smartsheet_jobs_sheet_id)


# Keep the client API honest: the generic client does not cache sheet configuration.
SmartsheetClient.access_sheet_id = property(lambda self: __import__("app.settings", fromlist=["settings"]).settings.smartsheet_jobs_sheet_id)
