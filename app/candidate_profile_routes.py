from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.candidate_profile import CandidateProfile
from app.candidate_profile_store import CandidateProfileStore
from app.database import get_db

router = APIRouter(prefix="/candidate-profile", tags=["candidate-profile"])
store = CandidateProfileStore()


@router.post("/validate", response_model=CandidateProfile)
def validate_profile(profile: CandidateProfile) -> CandidateProfile:
    """Validate and normalize a candidate profile."""
    return profile


@router.put("", response_model=CandidateProfile)
def save_candidate_profile(profile: CandidateProfile, db: Session = Depends(get_db)) -> CandidateProfile:
    """Persist the normalized candidate profile in PostgreSQL."""
    return store.save(db, profile)


@router.get("", response_model=CandidateProfile | None)
def get_candidate_profile(db: Session = Depends(get_db)) -> CandidateProfile | None:
    """Return the persisted candidate profile, if one exists."""
    return store.load(db)
