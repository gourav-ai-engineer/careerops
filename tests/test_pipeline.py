import asyncio

from app.career_pipeline import run_career_pipeline
from app.models import JobSourceEvidence


def test_full_pipeline_stops_safely_at_verification_gate(db_session):
    result = asyncio.run(
        run_career_pipeline(
            db_session,
            text="Example | Software Engineer | Remote | https://example.com/jobs/123",
        )
    )

    assert result.processed == 1
    item = result.items[0]
    assert item.ingestion.status == "persisted"
    assert item.screening.status in {"needs_review", "screened"}
    assert item.fit.status == "skipped"
    assert item.contacts.status == "skipped"
    assert item.required_action is not None

    evidence = db_session.query(JobSourceEvidence).all()
    assert len(evidence) == 1
    assert evidence[0].source_type == "initial_screening"
