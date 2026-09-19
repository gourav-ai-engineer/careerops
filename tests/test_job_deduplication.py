from app.job_deduplication import compare_jobs


def test_same_application_url_is_duplicate() -> None:
    result = compare_jobs(
        "Acme", "Python Engineer", "Remote", "https://jobs.acme.com/1/",
        "Different Name", "Different Title", "India", "https://jobs.acme.com/1",
    )
    assert result.is_duplicate is True
    assert result.confidence == 1.0


def test_similar_records_are_duplicate() -> None:
    result = compare_jobs(
        "Acme Technologies", "Senior Python Engineer", "Remote", None,
        "Acme Technologies", "Senior Python Engineer", "Remote", None,
    )
    assert result.is_duplicate is True
    assert result.confidence >= 0.88


def test_different_companies_are_not_duplicate() -> None:
    result = compare_jobs(
        "Acme", "Python Engineer", "Remote", None,
        "Globex", "Python Engineer", "Remote", None,
    )
    assert result.is_duplicate is False
