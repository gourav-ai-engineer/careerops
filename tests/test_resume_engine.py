from app.resume_engine import tailor_resume


def test_tailoring_preserves_master_and_reports_keywords():
    master = "Skills: Python, SQL\nExperience: Built APIs."
    result = tailor_resume(master, "Software Engineer", ["Python", "Docker"])
    assert result.content == master
    assert result.matched_keywords == ["Python"]
    assert result.missing_keywords == ["Docker"]
    assert result.change_plan
