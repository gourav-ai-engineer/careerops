from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.career_pipeline import run_career_pipeline
from app.database import get_db
from app.ingestion import IngestedJob, parse_csv_jobs, parse_whatsapp_export
from app.pipeline_ingestion import process_text
from app.run_service import finish_run, start_run

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRequest(BaseModel):
    text: str = Field(min_length=1)


class PipelineItemResponse(BaseModel):
    job_id: int
    company_name: str
    title: str
    persisted: bool
    duplicate: bool
    duplicate_confidence: float
    reason: str


class PipelineResponse(BaseModel):
    processed: int
    persisted: int
    duplicates: int
    items: list[PipelineItemResponse]
    run_id: int


class PipelineRunRequest(BaseModel):
    text: str = Field(min_length=1)
    live_check: bool = False
    discover_contacts: bool = False
    smartsheet_dry_run: bool = False
    generate_resume_drafts: bool = False


class StageResponse(BaseModel):
    status: str
    reason: str


class PipelineRunItemResponse(BaseModel):
    job_id: int
    company_name: str
    title: str
    ingestion: StageResponse
    screening: StageResponse
    live_check: StageResponse
    fit: StageResponse
    contacts: StageResponse
    resume: StageResponse
    smartsheet: StageResponse
    required_action: str | None = None


class PipelineRunResponse(BaseModel):
    run_id: int
    processed: int
    warnings: list[str]
    items: list[PipelineRunItemResponse]


@router.post("/ingest", response_model=PipelineResponse)
def ingest_pipeline(payload: PipelineRequest, db: Session = Depends(get_db)) -> PipelineResponse:
    run = start_run(db, "pipeline_ingest")
    try:
        results = process_text(db, payload.text)
        items = [
            PipelineItemResponse(
                job_id=result.job_id,
                company_name=result.extracted.company_name,
                title=result.extracted.title,
                persisted=result.persisted,
                duplicate=result.duplicate,
                duplicate_confidence=result.duplicate_confidence,
                reason=result.reason,
            )
            for result in results
        ]
        persisted = sum(item.persisted for item in items)
        duplicates = sum(item.duplicate for item in items)
        finish_run(
            db, run, status="succeeded", input_count=1, output_count=len(items),
            summary={"processed": len(items), "persisted": persisted, "duplicates": duplicates},
        )
        record_audit(db, entity_type="processing_run", entity_id=run.id, action="pipeline_ingest_completed")
        return PipelineResponse(
            processed=len(items), persisted=persisted, duplicates=duplicates,
            items=items, run_id=run.id,
        )
    except Exception as exc:
        finish_run(db, run, status="failed", error_count=1, error_message=str(exc))
        record_audit(db, entity_type="processing_run", entity_id=run.id, action="pipeline_ingest_failed")
        raise



def _records_to_text(records: list[IngestedJob]) -> str:
    lines: list[str] = []
    for item in records:
        parts = [item.company_name, item.title]
        if item.location:
            parts.append(item.location)
        suffix = f" {item.application_url}" if item.application_url else ""
        lines.append(" | ".join(parts) + suffix)
    return "\n".join(lines)


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(
    payload: PipelineRunRequest,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    result = await run_career_pipeline(
        db,
        text=payload.text,
        live_check=payload.live_check,
        discover_contacts=payload.discover_contacts,
        smartsheet_dry_run=payload.smartsheet_dry_run,
        generate_resume_drafts=payload.generate_resume_drafts,
    )
    return PipelineRunResponse(
        run_id=result.run_id,
        processed=result.processed,
        warnings=result.warnings,
        items=[
            PipelineRunItemResponse(
                job_id=item.job_id,
                company_name=item.company_name,
                title=item.title,
                ingestion=StageResponse(**item.ingestion.__dict__),
                screening=StageResponse(**item.screening.__dict__),
                live_check=StageResponse(**item.live_check.__dict__),
                fit=StageResponse(**item.fit.__dict__),
                contacts=StageResponse(**item.contacts.__dict__),
                resume=StageResponse(**item.resume.__dict__),
                smartsheet=StageResponse(**item.smartsheet.__dict__),
                required_action=item.required_action,
            )
            for item in result.items
        ],
    )



async def _run_uploaded_export(
    content: bytes,
    parser,
    *,
    live_check: bool,
    discover_contacts: bool,
    smartsheet_dry_run: bool,
    generate_resume_drafts: bool,
    db: Session,
) -> PipelineRunResponse:
    records = parser(content.decode("utf-8-sig"))
    if not records:
        return PipelineRunResponse(run_id=0, processed=0, warnings=["No supported job records were found in the uploaded file"], items=[])
    return await run_pipeline(
        PipelineRunRequest(
            text=_records_to_text(records),
            live_check=live_check,
            discover_contacts=discover_contacts,
            smartsheet_dry_run=smartsheet_dry_run,
            generate_resume_drafts=generate_resume_drafts,
        ),
        db,
    )


@router.post("/whatsapp-export", response_model=PipelineRunResponse)
async def run_whatsapp_export(
    file: UploadFile = File(...),
    live_check: bool = False,
    discover_contacts: bool = False,
    smartsheet_dry_run: bool = False,
    generate_resume_drafts: bool = False,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return await _run_uploaded_export(
        await file.read(),
        parse_whatsapp_export,
        live_check=live_check,
        discover_contacts=discover_contacts,
        smartsheet_dry_run=smartsheet_dry_run,
        generate_resume_drafts=generate_resume_drafts,
        db=db,
    )


@router.post("/csv", response_model=PipelineRunResponse)
async def run_csv_export(
    file: UploadFile = File(...),
    live_check: bool = False,
    discover_contacts: bool = False,
    smartsheet_dry_run: bool = False,
    generate_resume_drafts: bool = False,
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    return await _run_uploaded_export(
        await file.read(),
        parse_csv_jobs,
        live_check=live_check,
        discover_contacts=discover_contacts,
        smartsheet_dry_run=smartsheet_dry_run,
        generate_resume_drafts=generate_resume_drafts,
        db=db,
    )
