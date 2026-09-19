from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class CandidateProfile(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    target_role_families: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_keywords: list[str] = Field(default_factory=list)
    work_authorization: str | None = Field(default=None, max_length=255)

    @field_validator("target_role_families", "preferred_locations", "skills", "experience_keywords", mode="before")
    @classmethod
    def clean_lists(cls, values: list[str] | None) -> list[str]:
        if values is None:
            return []
        cleaned = {str(value).strip() for value in values if str(value).strip()}
        return sorted(cleaned, key=str.casefold)

    @field_validator("name", "work_authorization", mode="before")
    @classmethod
    def clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()
