from app.contact_discovery import PublicContactCandidate, normalize_phone, validate_public_contact


def test_valid_public_work_phone_candidate() -> None:
    candidate = PublicContactCandidate(
        name="Recruiting Team",
        title="University Recruiting",
        phone="+91 80 1234 5678",
        phone_type="official_recruitment_helpline",
        source_url="https://example.com/careers/contact",
        verification_status="source_checked",
    )

    assert validate_public_contact(candidate) == []


def test_rejects_unknown_phone_type() -> None:
    candidate = PublicContactCandidate(
        name="Unknown",
        title="Recruiter",
        phone="+91 99999 99999",
        phone_type="personal_mobile",
        source_url="https://example.com/profile",
        verification_status="source_checked",
    )

    assert "phone_type must describe an allowed professional number" in validate_public_contact(candidate)


def test_normalize_phone_does_not_infer_country_code() -> None:
    assert normalize_phone("  +91   80  1234 5678 ") == "+91 80 1234 5678"
    assert normalize_phone("   ") is None
