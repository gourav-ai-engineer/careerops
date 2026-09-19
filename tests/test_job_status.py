import pytest

from app.job_status import validate_transition


def test_valid_transition_from_discovered_to_verified() -> None:
    validate_transition("discovered", "verified")


def test_valid_transition_from_applied_to_interview() -> None:
    validate_transition("applied", "interview")


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(ValueError, match="Invalid status transition"):
        validate_transition("discovered", "applied")


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported status"):
        validate_transition("discovered", "something_else")


def test_same_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="already in the requested status"):
        validate_transition("verified", "verified")
