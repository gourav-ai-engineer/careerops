from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.pipeline_ingestion import process_text

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


@router.post("/ingest", response_model=PipelineResponse)
def ingest_pipeline(payload: PipelineRequest, db: Session = Depends(get_db)) -> PipelineResponse:
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
    return PipelineResponse(
        processed=len(items),
        persisted=sum(item.persisted for item in items),
        duplicates=sum(item.duplicate for item in items),
        items=items,
    )
