import pytest
from pydantic import ValidationError

from app.job_verification_routes import SourceEvidenceRequest


def test_supported_status_is_accepted() -> None:
    request = SourceEvidenceRequest(
        source_url="https://careers.example.com/role",
        verification_status="screened",
    )
    assert request.verification_status == "screened"


def test_unsupported_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceEvidenceRequest(
            source_url="https://careers.example.com/role",
            verification_status="trusted_without_review",
        )
