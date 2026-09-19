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
- Provider-independent contact discovery adapters.
- Public professional contact discovery from supplied HTTPS pages on the configured company domain.
- Contact evidence records containing provider, source, verification state, confidence, and timestamp.

## Job verification

CareerOps distinguishes screening from verification. A company-domain match is evidence that a URL is hosted on the stored employer domain or a subdomain; it is not proof of job ownership by itself. A job is marked verified only through an explicit verification decision, which is stored together with source evidence and status history.

## Candidate fit

For verified and later-stage jobs, CareerOps can compare persisted job requirements with the saved candidate profile. The assessment records matched and missing skills, role-family match, location match, eligibility match, a 0–100 rule-based score, and a human-readable explanation.

## Contact discovery

Contact discovery uses a provider adapter contract so future services can be added without rewriting the persistence layer. The current provider is an official-website adapter that reads public business contact details only from HTTPS pages on the supplied employer domain or subdomains.

Endpoint:

POST /contacts/discover

Example payload fields:

- company_name
- company_domain
- source_urls
- role_keywords
- optional job_id

The result includes the provider used, discovered contacts, source URL, phone type, verification state, and confidence.

## Run locally

powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

Open the interactive API documentation at http://127.0.0.1:8000/docs.

## Contact-data safety rules

CareerOps only accepts legitimately published professional contact information, such as company switchboards, official recruitment helplines, and publicly listed work phones. It does not infer numbers, bypass logins, scrape private profiles, or store private/personal mobile numbers.

## Planned next steps

1. Add additional compliant contact-provider adapters with explicit credentials and rate limits.
2. Add Smartsheet dry-run and synchronization.
3. Add scheduled discovery and monitoring.
4. Add dashboard views for verification, fit, contacts, and application progress.
