from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProcessingRun
from app.run_service import list_runs

router = APIRouter(prefix="/runs", tags=["runs"])


def _serialize(run: ProcessingRun) -> dict:
    return {
        "id": run.id, "run_type": run.run_type, "status": run.status,
        "correlation_id": run.correlation_id, "input_count": run.input_count,
        "output_count": run.output_count, "error_count": run.error_count,
        "summary": run.summary, "error_message": run.error_message,
        "started_at": run.started_at, "finished_at": run.finished_at,
    }


@router.get("")
def get_runs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)) -> list[dict]:
    return [_serialize(run) for run in list_runs(db, limit=limit)]
