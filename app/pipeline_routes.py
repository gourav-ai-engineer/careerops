from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import record_audit
from app.database import get_db
from app.pipeline_ingestion import process_text
from app.run_service import finish_run, start_run

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRequest(BaseModel):
    text: str = Field(min_length=1)


class PipelineItemResponse(BaseModel):
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


@router.post("/ingest", response_model=PipelineResponse)
def ingest_pipeline(payload: PipelineRequest, db: Session = Depends(get_db)) -> PipelineResponse:
    run = start_run(db, "pipeline_ingest")
    try:
        results = process_text(db, payload.text)
        items = [
            PipelineItemResponse(
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
        return PipelineResponse(processed=len(items), persisted=persisted, duplicates=duplicates, items=items, run_id=run.id)
    except Exception as exc:
        finish_run(db, run, status="failed", error_count=1, error_message=str(exc))
        record_audit(db, entity_type="processing_run", entity_id=run.id, action="pipeline_ingest_failed")
        raise
