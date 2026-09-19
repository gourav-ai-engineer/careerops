from app.contact_quality import find_duplicate_contacts, merge_contacts
from app.models import Company, Contact, Job, JobContact


def test_duplicate_detection_and_merge(db_session):
    company = Company(name="Example", normalized_name="example", domain="example.com")
    db_session.add(company)
    db_session.flush()
    first = Contact(company_id=company.id, name="A", phone="123", source_url="https://example.com")
    second = Contact(company_id=company.id, name="A", phone="123", source_url="https://example.com")
    db_session.add_all([first, second])
    db_session.flush()
    job = Job(company_id=company.id, title="Engineer", application_url="https://example.com/jobs/1")
    db_session.add(job)
    db_session.flush()
    db_session.add(JobContact(job_id=job.id, contact_id=second.id))
    db_session.commit()

    duplicates = find_duplicate_contacts(db_session)
    assert any(item.duplicate_id == second.id for item in duplicates)

    merged = merge_contacts(db_session, first.id, second.id)
    assert merged.id == first.id
    assert db_session.get(Contact, second.id) is None
