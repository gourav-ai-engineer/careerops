from __future__ import annotations

import json
from pathlib import Path

from app.candidate_profile import CandidateProfile


class CandidateProfileStore:
    """Small JSON-backed profile store; replaceable with PostgreSQL repository later."""

    def __init__(self, path: str = "data/candidate_profile.json") -> None:
        self.path = Path(path)

    def save(self, profile: CandidateProfile) -> CandidateProfile:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile

    def load(self) -> CandidateProfile | None:
        if not self.path.exists():
            return None
        return CandidateProfile.model_validate(json.loads(self.path.read_text(encoding="utf-8")))
