from app.job_intake import canonical_url, job_fingerprint, normalize_text


def test_normalize_text_collapses_whitespace_and_case() -> None:
    assert normalize_text("  Backend   Engineer\nIntern ") == "backend engineer intern"
    assert normalize_text(None) == ""


def test_canonical_url_removes_query_fragment_and_trailing_slash() -> None:
    assert canonical_url("HTTPS://Example.COM/jobs/123/?utm_source=chat#apply") == "https://example.com/jobs/123"
    assert canonical_url(None) == ""


def test_job_fingerprint_is_deterministic() -> None:
    first = job_fingerprint("Acme", "Backend Engineer", "India", "https://example.com/jobs/1/")
    second = job_fingerprint(" acme ", "backend engineer", "india", "HTTPS://EXAMPLE.COM/jobs/1?x=1")
    assert first == second
    assert len(first) == 64


def test_job_fingerprint_changes_for_different_jobs() -> None:
    first = job_fingerprint("Acme", "Backend Engineer", "India", "https://example.com/jobs/1")
    second = job_fingerprint("Acme", "Backend Engineer", "India", "https://example.com/jobs/2")
    assert first != second
