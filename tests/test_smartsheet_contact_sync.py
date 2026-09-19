from app.models import Company, Contact, Job
from app.smartsheet_contact_sync import build_contact_sync_plan


def _job_with_contact() -> Job:
    company = Company(id=1, name="Example", normalized_name="example", domain="example.com")
    contact = Contact(
        id=20,
        company_id=1,
        company=company,
        name="Recruiting Team",
        title="University Recruiting",
        email="recruiting@example.com",
        phone="+91 80 1234 5678",
        phone_type="official_recruitment_helpline",
        linkedin_url="https://www.linkedin.com/company/example",
        verification_status="verified",
        verification_confidence="high",
    )
    job = Job(
        id=10,
        company=company,
        company_id=1,
        title="AI Engineer",
        application_url="https://example.com/jobs/1",
        status="verified",
    )
    job.contacts = []
    job.contacts.append(type("Link", (), {"contact": contact, "contact_id": contact.id})())
    return job


def test_contact_sync_updates_existing_job_row() -> None:
    job = _job_with_contact()
    sheet = {
        "id": 123,
        "rows": [{
            "id": 99,
            "cells": [
                {"columnId": 5398779437813636, "value": "Example"},
                {"columnId": 3146979624128388, "value": "AI Engineer"},
                {"columnId": 191492368666500, "value": "https://example.com/jobs/1"},
            ],
        }],
    }
    plan = build_contact_sync_plan([job], sheet)
    assert len(plan.operations) == 1
    assert plan.operations[0].action == "update"
    assert plan.operations[0].row_id == 99
    assert 6946891809722244 in {cell["columnId"] for cell in plan.operations[0].cells}


def test_contact_sync_skips_unverified_contacts() -> None:
    company = Company(id=1, name="Example", normalized_name="example", domain="example.com")
    contact = Contact(id=20, company_id=1, company=company, name="Unknown", verification_status="unverified")
    job = Job(id=10, company=company, company_id=1, title="AI Engineer", status="verified")
    job.contacts = [type("Link", (), {"contact": contact, "contact_id": contact.id})()]
    plan = build_contact_sync_plan([job], {"id": 123, "rows": []})
    assert plan.operations[0].action == "skip"


def test_contact_sync_does_not_add_missing_job_rows() -> None:
    job = _job_with_contact()
    plan = build_contact_sync_plan([job], {"id": 123, "rows": []})
    assert plan.operations[0].action == "skip"
    assert "sync the job" in plan.operations[0].reason
