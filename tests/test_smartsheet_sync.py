from app.models import Company, Job
from app.smartsheet_sync import build_job_sync_plan


def _job() -> Job:
    company = Company(id=1, name="Example", normalized_name="example", domain="example.com")
    return Job(
        id=10,
        company=company,
        company_id=1,
        title="AI Engineer",
        location="Remote",
        eligibility="India",
        application_url="https://example.com/jobs/1",
        source_url="https://example.com/careers",
        status="verified",
    )


def test_new_job_creates_add_operation() -> None:
    job = _job()
    plan = build_job_sync_plan([job], {"id": 123, "rows": []}, {10: 88})
    assert len(plan.operations) == 1
    assert plan.operations[0].action == "add"


def test_matching_job_with_same_fields_is_unchanged() -> None:
    job = _job()
    cells = [
        {"columnId": 5398779437813636, "value": "Example"},
        {"columnId": 3146979624128388, "value": "AI Engineer"},
        {"columnId": 7650579251498884, "value": "Remote"},
        {"columnId": 2021079717285764, "value": "India"},
        {"columnId": 8776479158341508, "value": "verified"},
        {"columnId": 191492368666500, "value": "https://example.com/jobs/1"},
        {"columnId": 4695091996036996, "value": "https://example.com/careers"},
    ]
    sheet = {"id": 123, "rows": [{"id": 99, "cells": cells}]}
    plan = build_job_sync_plan([job], sheet)
    assert plan.operations == ()


def test_changed_status_creates_update_operation() -> None:
    job = _job()
    cells = [
        {"columnId": 5398779437813636, "value": "Example"},
        {"columnId": 3146979624128388, "value": "AI Engineer"},
        {"columnId": 7650579251498884, "value": "Remote"},
        {"columnId": 2021079717285764, "value": "India"},
        {"columnId": 8776479158341508, "value": "shortlisted"},
        {"columnId": 191492368666500, "value": "https://example.com/jobs/1"},
        {"columnId": 4695091996036996, "value": "https://example.com/careers"},
    ]
    sheet = {"id": 123, "rows": [{"id": 99, "cells": cells}]}
    plan = build_job_sync_plan([job], sheet)
    assert len(plan.operations) == 1
    assert plan.operations[0].action == "update"
    assert plan.operations[0].row_id == 99


def test_unique_company_role_fallback_matches_when_apply_link_is_blank() -> None:
    job = _job()
    cells = [
        {"columnId": 5398779437813636, "value": "Example"},
        {"columnId": 3146979624128388, "value": "AI Engineer"},
        {"columnId": 8776479158341508, "value": "verified"},
    ]
    sheet = {"id": 123, "rows": [{"id": 77, "cells": cells}]}
    plan = build_job_sync_plan([job], sheet)
    assert len(plan.operations) == 1
    assert plan.operations[0].action == "update"
    assert plan.operations[0].row_id == 77
