from fastapi import APIRouter

from app.candidate_profile import CandidateProfile
from app.candidate_profile_store import CandidateProfileStore

router = APIRouter(prefix="/candidate-profile", tags=["candidate-profile"])
store = CandidateProfileStore()


@router.post("/validate", response_model=CandidateProfile)
def validate_profile(profile: CandidateProfile) -> CandidateProfile:
    """Validate and normalize a candidate profile before it is used for scoring."""
    return profile


@router.put("", response_model=CandidateProfile)
def save_candidate_profile(profile: CandidateProfile) -> CandidateProfile:
    """Persist the normalized candidate profile."""
    return store.save(profile)


@router.get("", response_model=CandidateProfile | None)
def get_candidate_profile() -> CandidateProfile | None:
    """Return the persisted candidate profile, if one exists."""
    return store.load()
