from app.ingestion import IngestedJob


def test_ingested_job_defaults_are_safe() -> None:
    job = IngestedJob(company_name="Acme", title="ML Engineer")
    assert job.location is None
    assert job.application_url is None
    assert job.source_url is None
