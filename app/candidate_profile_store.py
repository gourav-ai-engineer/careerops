from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.candidate_profile import CandidateProfile
from app.models import CandidateProfileRecord


class CandidateProfileStore:
    """PostgreSQL-backed single-user candidate profile store."""

    def save(self, db: Session, profile: CandidateProfile) -> CandidateProfile:
        record = db.scalar(select(CandidateProfileRecord).where(CandidateProfileRecord.id == 1))
        values = profile.model_dump()
        if record is None:
            record = CandidateProfileRecord(id=1)
            db.add(record)
        record.name = values["name"]
        record.target_role_families = json.dumps(values["target_role_families"])
        record.preferred_locations = json.dumps(values["preferred_locations"])
        record.skills = json.dumps(values["skills"])
        record.experience_keywords = json.dumps(values["experience_keywords"])
        record.work_authorization = values["work_authorization"]
        db.commit()
        return profile

    def load(self, db: Session) -> CandidateProfile | None:
        record = db.scalar(select(CandidateProfileRecord).where(CandidateProfileRecord.id == 1))
        if record is None:
            return None
        return CandidateProfile(
            name=record.name,
            target_role_families=json.loads(record.target_role_families),
            preferred_locations=json.loads(record.preferred_locations),
            skills=json.loads(record.skills),
            experience_keywords=json.loads(record.experience_keywords),
            work_authorization=record.work_authorization,
        )
