from app.ingestion import parse_csv_jobs, parse_whatsapp_export


def test_parse_csv_jobs() -> None:
    content = "company,title,location,apply_url\nAcme,Backend Intern,India,https://acme.example/jobs/1\n"
    jobs = parse_csv_jobs(content)
    assert len(jobs) == 1
    assert jobs[0].company_name == "Acme"
    assert jobs[0].application_url == "https://acme.example/jobs/1"


def test_parse_whatsapp_export_supported_pipe_format() -> None:
    content = "[19/09/2026, 08:00] User - Acme | ML Intern | Remote https://acme.example/apply\n"
    jobs = parse_whatsapp_export(content)
    assert len(jobs) == 1
    assert jobs[0].title == "ML Intern"
    assert jobs[0].application_url == "https://acme.example/apply"
