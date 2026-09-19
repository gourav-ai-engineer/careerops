# CareerOps

CareerOps is a safety-first career intelligence pipeline for India-based AI/ML, GenAI, software, backend, and data opportunities, including NIT Silchar campus hiring.

## Current capabilities

- FastAPI service with a health endpoint.
- PostgreSQL/SQLAlchemy foundation for companies, jobs, contacts, and job-contact relationships.
- Job ingestion, deterministic deduplication, search, pagination, detail retrieval, and status lifecycle.
- Conservative official-source screening with persisted job-source evidence.
- Explicit verification decisions that move jobs through the lifecycle with an auditable status history.
- Extracted job requirements persisted for downstream matching.
- Candidate-profile validation and deterministic profile-based fit assessment.
- Persistent fit assessments that can be recalculated idempotently.
- Public contact validation helpers.
- Professional phone metadata fields with explicit phone type, source, verification status, and confidence.

## Job verification

CareerOps distinguishes screening from verification. A company-domain match is evidence that a URL is hosted on the stored employer domain or a subdomain; it is not proof of job ownership by itself. A job is marked verified only through an explicit verification decision, which is stored together with source evidence and status history.

## Candidate fit

For verified and later-stage jobs, CareerOps can automatically compare the persisted job requirements with the saved candidate profile. The assessment records matched and missing skills, role-family match, location match, eligibility match, a 0–100 rule-based score, and a human-readable explanation.

Endpoints:

GET   /jobs
GET   /jobs/{job_id}
PATCH /jobs/{job_id}/status
POST  /jobs/{job_id}/verification
POST  /jobs/{job_id}/fit-assessment
GET   /jobs/{job_id}/fit-assessment
POST  /jobs/fit-assessments/verified
GET   /jobs/fit-assessments/verified
POST  /jobs/{job_id}/source-evidence
GET   /jobs/{job_id}/source-evidence

## Run locally

powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Open the interactive API documentation at http://127.0.0.1:8000/docs.

## Contact-data safety rules

CareerOps only accepts legitimately published professional contact information, such as company switchboards, official recruitment helplines, and publicly listed work phones. It does not infer numbers, bypass logins, scrape private profiles, or store private/personal mobile numbers.

## Planned next steps

1. Add contact discovery adapters with evidence and provider metadata.
2. Add Smartsheet dry-run and synchronization.
3. Add scheduled discovery and monitoring.
4. Add dashboard views for verification, fit, contacts, and application progress.
