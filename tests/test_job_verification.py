from app.job_verification import verify_job_source


def test_missing_source_needs_review() -> None:
    result = verify_job_source(None, None)
    assert result.status == "needs_review"


def test_invalid_scheme_is_rejected() -> None:
    result = verify_job_source("ftp://jobs.example.com/role", None)
    assert result.status == "rejected"


def test_careers_host_is_only_screened() -> None:
    result = verify_job_source("https://careers.example.com/role", None)
    assert result.status == "screened"
    assert "verify ownership" in result.reason


def test_regular_https_url_needs_review() -> None:
    result = verify_job_source("https://example.com/jobs/1", None)
    assert result.status == "needs_review"
