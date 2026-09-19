# CareerOps

CareerOps is a safety-first career intelligence pipeline for India-based AI/ML, GenAI, software, backend, and data opportunities, including NIT Silchar campus hiring.

## Current capabilities

- FastAPI service with a health endpoint.
- PostgreSQL/SQLAlchemy foundation for companies, jobs, job-contact relationships, requirements, fit assessments, contact evidence, and status history.
- Job ingestion, deterministic deduplication, search, pagination, detail retrieval, and status lifecycle.
- Conservative official-source screening with persisted job-source evidence.
- Explicit verification decisions with an auditable status history.
- Extracted job requirements persisted for downstream matching.
- Candidate-profile validation and deterministic profile-based fit assessment.
- Persistent fit assessments that can be recalculated idempotently.
- Provider-independent public contact discovery adapters and contact evidence records.
- Smartsheet dry-run planning and idempotent job synchronization for verified/later-stage jobs.
- Smartsheet contact synchronization for linked, source-checked/verified public professional contacts.

## Smartsheet synchronization

The existing AI & SDE job tracker uses Company, Role, Location, Eligibility, Fit Score, Application Status, Apply Link, Source, Last Checked, Recruiter / Contact, Recruiter LinkedIn, and Recruiter Verification.

Job endpoints:

    POST /sync/smartsheet/dry-run
    POST /sync/smartsheet/apply

Contact endpoints:

    POST /sync/smartsheet/contacts/dry-run
    POST /sync/smartsheet/contacts/apply

Contact synchronization updates existing job rows only. It does not invent LinkedIn URLs or contact data. Only contact records with source_checked or verified status are synchronized.

Local configuration:

    SMARTSHEET_ACCESS_TOKEN=<local-secret>
    SMARTSHEET_JOBS_SHEET_ID=3084190078947204

## Job verification

CareerOps distinguishes screening from verification. A company-domain match is evidence that a URL is hosted on the stored employer domain or a subdomain; it is not proof of job ownership by itself. A job is marked verified only through an explicit verification decision, which is stored together with source evidence and status history.

## Candidate fit

For verified and later-stage jobs, CareerOps can compare persisted job requirements with the saved candidate profile. The assessment records matched and missing skills, role-family match, location match, eligibility match, a 0–100 rule-based score, and a human-readable explanation.

## Contact discovery

Contact discovery uses a provider adapter contract so future services can be added without rewriting the persistence layer. The current provider reads public business contact details only from HTTPS pages on the supplied employer domain or subdomains.

## Database setup

For existing databases after the recruiter LinkedIn field was added, run:

    .\.venv\Scripts\python.exe -m app.init_db

This creates missing tables and applies the contact LinkedIn column migration.

## Run locally

    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Open the interactive API documentation at http://127.0.0.1:8000/docs.

## Contact-data safety rules

CareerOps only accepts legitimately published professional contact information, such as company switchboards, official recruitment helplines, and publicly listed work phones. It does not infer numbers, bypass logins, scrape private profiles, or store private/personal mobile numbers.

## Planned next steps

1. Add additional compliant contact-provider adapters with explicit credentials and rate limits.
2. Add scheduled discovery and monitoring.
3. Add dashboard views for verification, fit, contacts, and application progress.
4. Add stronger migration management with Alembic.
