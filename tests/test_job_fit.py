from app.job_fit import score_job_fit


def test_fit_score_matches_and_missing_skills() -> None:
    result = score_job_fit(["Python", "PyTorch", "SQL"], ["python", "sql"], True, True)
    assert result.score == 77
    assert result.matched_skills == ["python", "sql"]
    assert result.missing_skills == ["pytorch"]


def test_unknown_constraints_are_neutral() -> None:
    result = score_job_fit([], ["python"])
    assert result.score == 85
