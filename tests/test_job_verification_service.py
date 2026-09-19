from app.job_verification_service import verify_and_record
from app.models import Job


def test_verification_requires_source_url() -> None:
    job = Job(status="discovered", application_url=None, source_url=None)
    try:
        verify_and_record(None, job, decision="verified")
    except ValueError as exc:
        assert "no application_url or source_url" in str(exc)
    else:
        raise AssertionError("Expected verification to require evidence URL")
