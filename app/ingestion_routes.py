from fastapi import APIRouter, File, UploadFile

from app.ingestion import parse_csv_jobs, parse_whatsapp_export

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...)) -> dict[str, object]:
    content = (await file.read()).decode("utf-8-sig")
    jobs = parse_csv_jobs(content)
    return {"count": len(jobs), "jobs": [job.__dict__ for job in jobs]}


@router.post("/whatsapp-export")
async def ingest_whatsapp_export(file: UploadFile = File(...)) -> dict[str, object]:
    content = (await file.read()).decode("utf-8-sig")
    jobs = parse_whatsapp_export(content)
    return {"count": len(jobs), "jobs": [job.__dict__ for job in jobs]}
