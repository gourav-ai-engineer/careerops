from app.candidate_profile import CandidateProfile
from app.candidate_fit import assess_candidate_fit
from app.models import Job, JobRequirement


def test_candidate_fit_uses_profile_and_job_requirements() -> None:
    job = Job(
        status="verified",
        title="AI Engineer",
        role_family="AI/ML",
        location="Remote",
        eligibility="India work authorization",
    )
    job.requirements = JobRequirement(required_skills='["Python", "PyTorch"]')

    profile = CandidateProfile(
        name="Candidate",
        target_role_families=["AI/ML"],
        preferred_locations=["Remote"],
        skills=["Python", "FastAPI"],
        work_authorization="India",
    )

    result = assess_candidate_fit(job, profile)

    assert result.matched_skills == ["Python"]
    assert result.missing_skills == ["PyTorch"]
    assert result.role_match is True
    assert result.location_match is True
    assert result.eligibility_match is True
    assert result.score == 75


def test_candidate_fit_does_not_penalize_unknown_dimensions_as_mismatches() -> None:
    job = Job(status="verified", title="Software Engineer")
    profile = CandidateProfile(name="Candidate", skills=["Python"])

    result = assess_candidate_fit(job, profile, required_skills=["Python"])

    assert result.score == 74
    assert result.role_match is None
    assert result.location_match is None
    assert result.eligibility_match is None
