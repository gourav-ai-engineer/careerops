from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.job_extraction import ExtractedJob, extract_jobs

router = APIRouter(prefix="/extraction", tags=["extraction"])


class ExtractionRequest(BaseModel):
    text: str = Field(min_length=1)


class ExtractionResponse(BaseModel):
    jobs: list[ExtractedJob]
    warnings: list[str]


@router.post("/jobs", response_model=ExtractionResponse)
def extract_job_records(payload: ExtractionRequest) -> ExtractionResponse:
    result = extract_jobs(payload.text)
    return ExtractionResponse(jobs=result.jobs, warnings=result.warnings)
