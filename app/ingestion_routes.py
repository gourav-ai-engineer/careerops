from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import parse_csv_jobs, parse_whatsapp_export, persist_jobs

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/csv")
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    content = (await file.read()).decode("utf-8-sig")
    jobs = parse_csv_jobs(content)
    summary = persist_jobs(db, jobs)
    return {"count": len(jobs), "persistence": summary, "jobs": [job.__dict__ for job in jobs]}


@router.post("/whatsapp-export")
async def ingest_whatsapp_export(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    content = (await file.read()).decode("utf-8-sig")
    jobs = parse_whatsapp_export(content)
    summary = persist_jobs(db, jobs)
    return {"count": len(jobs), "persistence": summary, "jobs": [job.__dict__ for job in jobs]}
