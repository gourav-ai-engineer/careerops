from fastapi import APIRouter

from app.candidate_profile import CandidateProfile

router = APIRouter(prefix="/candidate-profile", tags=["candidate-profile"])


@router.post("/validate", response_model=CandidateProfile)
def validate_profile(profile: CandidateProfile) -> CandidateProfile:
    """Validate and normalize a candidate profile before it is used for scoring."""
    return profile
