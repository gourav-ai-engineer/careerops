from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcessingRun


def start_run(db: Session, run_type: str, input_count: int = 0) -> ProcessingRun:
    run = ProcessingRun(run_type=run_type, status="running", correlation_id=uuid.uuid4().hex, input_count=input_count)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_run(db: Session, run: ProcessingRun, *, status: str, output_count: int = 0,
               error_count: int = 0, summary: dict | None = None, error_message: str | None = None) -> ProcessingRun:
    run.status = status
    run.output_count = output_count
    run.error_count = error_count
    run.summary = json.dumps(summary or {}, sort_keys=True)
    run.error_message = error_message
    run.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def list_runs(db: Session, limit: int = 50) -> list[ProcessingRun]:
    return list(db.scalars(select(ProcessingRun).order_by(ProcessingRun.started_at.desc(), ProcessingRun.id.desc()).limit(limit)))
