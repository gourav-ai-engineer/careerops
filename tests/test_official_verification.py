from app.official_verification import verify_official_domain


def test_matching_company_subdomain_is_screened() -> None:
    result = verify_official_domain("https://careers.example.com/jobs/1", "example.com")
    assert result.status == "screened"
    assert result.candidate_host == "careers.example.com"


def test_different_domain_requires_review() -> None:
    result = verify_official_domain("https://jobs.vendor.com/1", "example.com")
    assert result.status == "needs_review"


def test_missing_company_domain_requires_review() -> None:
    result = verify_official_domain("https://example.com/jobs/1", None)
    assert result.status == "needs_review"
