# CareerOps

CareerOps is a safety-first career intelligence platform for India-based AI/ML, GenAI, software, backend, platform, and data opportunities, including NIT Silchar campus hiring.

## Complete platform

The planned application architecture is implemented across the API, database, provider layer, dashboard, synchronization layer, resume workflow, and scheduled-workflow integration.

Core capabilities:
- FastAPI service with health/readiness checks, request IDs, logging, optional API-key protection, and CORS.
- PostgreSQL source of truth for jobs, companies, requirements, verification evidence, lifecycle history, fit assessments, contacts, provider evidence, job-contact links, processing runs, audit events, master resume versions, and resume drafts.
- CSV and WhatsApp-export ingestion, typed extraction, deterministic deduplication, search, pagination, and lifecycle transitions.
- Official employer-domain screening and live HTTPS source checking with redirect validation.
- Explicit verification decisions with durable evidence.
- Candidate profile persistence and explainable fit assessment.
- Provider-based public professional contact discovery with an official-site adapter and optional Hunter source-backed professional email adapter.
- Provider rate limiting and retry runtime.
- Contact duplicate detection and explicit merge.
- Smartsheet dry-run/apply synchronization for verified/later-stage jobs and linked professional contacts.
- Master resume storage and reviewable job drafts that never invent claims and never overwrite the master automatically.
- Processing-run records, audit events, and request correlation IDs.
- Next.js operator dashboard.
- Docker Compose for PostgreSQL, API, and dashboard.
- Windmill-ready orchestration scripts.

## API surface

System: GET /, GET /health, GET /health/db
Jobs: GET /jobs, GET /jobs/{id}, POST /jobs/intake, PATCH /jobs/{id}/company-domain, PATCH /jobs/{id}/status, POST /jobs/{id}/verify-live, POST /jobs/{id}/fit-assessment, POST /jobs/fit-assessments/verified
Ingestion: POST /ingestion/csv, POST /ingestion/whatsapp-export, POST /pipeline/csv, POST /pipeline/whatsapp-export, POST /pipeline/ingest, POST /pipeline/run, POST /extraction/jobs
Contacts: POST /contacts, POST /contacts/discover, GET /contacts/list, GET /contacts/duplicates, POST /contacts/merge
Resume: GET /resume/master, PUT /resume/master, POST /resume/drafts/{job_id}, GET /resume/drafts, PATCH /resume/drafts/{draft_id}
Dashboard: GET /dashboard/summary
Runs: GET /runs
Smartsheet: POST /sync/smartsheet/dry-run, POST /sync/smartsheet/apply, POST /sync/smartsheet/contacts/dry-run, POST /sync/smartsheet/contacts/apply

## Local setup

Copy .env.example to .env. Run docker compose up --build, or install the Python package in a virtual environment and run python -m app.init_db.
Open http://localhost:3000 for the dashboard or http://localhost:8000/docs for the API.

Important variables include DATABASE_URL, SMARTSHEET_ACCESS_TOKEN, SMARTSHEET_JOBS_SHEET_ID, SMARTSHEET_CAMPUS_SHEET_ID, HUNTER_API_KEY, API_KEY, FRONTEND_ORIGIN, HTTP_TIMEOUT_SECONDS, PROVIDER_REQUESTS_PER_MINUTE, and LOG_LEVEL.

Never commit .env, tokens, API keys, or private contact data.

## Full pipeline endpoint

Use POST /pipeline/run for staged end-to-end execution from text. Use POST /pipeline/csv or POST /pipeline/whatsapp-export for uploaded source files; they normalize the upload into the same pipeline. Its flags are live_check, discover_contacts, smartsheet_dry_run, and generate_resume_drafts. The endpoint never auto-verifies a job and never applies Smartsheet writes. Those gates stay explicit so every external action remains reviewable.

Operational sequence: ingest -> extract/normalize -> deduplicate -> official-source screening -> optional live check -> explicit verification -> fit -> public professional contacts -> Smartsheet dry-run -> reviewed apply -> resume draft review.

PostgreSQL is the system of record. Smartsheet is the operational view. No workflow submits applications automatically.

## Safety

Only source-backed professional contact information is supported. The platform does not infer personal phone numbers, bypass authentication, scrape private profiles, or treat inferred contact data as verified. Resume drafts are reviewable and require explicit approval before use.

## Status

Implementation is complete for the planned architecture. The next step is the dedicated integration and acceptance test pass on the connected environment.
