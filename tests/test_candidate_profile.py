import pytest
from pydantic import ValidationError

from app.candidate_profile import CandidateProfile


def test_profile_normalizes_lists() -> None:
    profile = CandidateProfile(name=" Gourav ", skills=[" Python ", "Python", "PyTorch"])
    assert profile.name == "Gourav"
    assert profile.skills == ["PyTorch", "Python"]


def test_profile_requires_name() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(name="")
