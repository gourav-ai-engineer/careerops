from app.job_verification import host_matches_domain, verify_job_source


def test_exact_domain_matches() -> None:
    assert host_matches_domain("https://example.com/jobs/1", "example.com")


def test_subdomain_matches() -> None:
    assert host_matches_domain("https://careers.example.com/role", "example.com")


def test_lookalike_domain_does_not_match() -> None:
    assert not host_matches_domain("https://example.com.evil.test/role", "example.com")


def test_matching_company_domain_is_screened() -> None:
    result = verify_job_source(
        "https://careers.example.com/role",
        None,
        "example.com",
    )
    assert result.status == "screened"
    assert "stored company domain" in result.reason
