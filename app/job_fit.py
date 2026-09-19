from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FitResult:
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    eligibility_match: bool | None
    location_match: bool | None
    explanation: str


def _tokens(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def score_job_fit(
    required_skills: list[str],
    candidate_skills: list[str],
    eligibility_match: bool | None = None,
    location_match: bool | None = None,
) -> FitResult:
    required = _tokens(required_skills)
    candidate = _tokens(candidate_skills)
    matched = sorted(required & candidate)
    missing = sorted(required - candidate)
    skill_score = round((len(matched) / len(required)) * 70) if required else 70
    eligibility_score = 20 if eligibility_match is True else 0 if eligibility_match is False else 10
    location_score = 10 if location_match is True else 0 if location_match is False else 5
    score = min(100, skill_score + eligibility_score + location_score)
    explanation = (
        f"Matched {len(matched)}/{len(required)} required skills; "
        f"eligibility={eligibility_match}; location={location_match}."
    )
    return FitResult(score, matched, missing, eligibility_match, location_match, explanation)
