# CareerOps Local Testing

## Start with Docker

Run from the repository root:

    docker compose up --build

Wait until the API container reports that PostgreSQL is healthy.

Open:
- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- Database health: http://localhost:8000/health/db

## Run the complete pipeline with text

Example:

    curl -X POST http://localhost:8000/pipeline/run ^
      -H "Content-Type: application/json" ^
      -d "{"text":"Example | Software Engineer | Remote | https://example.com/jobs/123"}"

The response reports every stage. A newly discovered job stops at the explicit verification gate.

## Test with a WhatsApp export

In Swagger, use:

    POST /pipeline/whatsapp-export

Upload the exported .txt file.

The supported job line format is:

    Company | Role | Location | URL

WhatsApp timestamps and the "Messages and calls are end-to-end encrypted" header are ignored by the parser.

## Configure the employer domain

After ingestion, set the employer's official domain explicitly:

    PATCH /jobs/{job_id}/company-domain

Example JSON:

    {"company_domain":"example.com"}

This is deliberately separate from extracting a URL from a source message so an ATS host is not silently treated as the employer's domain.

## Verify the job

Use:

    POST /jobs/{job_id}/verification

Choose:

    {"decision":"verified","reason":"Reviewed official employer source"}

Verification is intentionally explicit. CareerOps never auto-verifies a job from a URL match alone.

## Continue downstream

After verification:

    POST /jobs/{job_id}/fit-assessment

For all verified jobs:

    POST /jobs/fit-assessments/verified

Public professional contact discovery:

    POST /contacts/discover

Resume:

    PUT /resume/master
    POST /resume/drafts/{job_id}

Smartsheet:

    POST /sync/smartsheet/dry-run
    POST /sync/smartsheet/apply

Always preview Smartsheet changes before apply.

## Test the dashboard

Refresh http://localhost:3000 after adding data. The dashboard exposes:
- Overview
- Jobs
- Contacts
- Resume master/drafts
- Fit recalculation
- API documentation link

## Run the automated test suite

After installing the project locally:

    .\.venv\Scripts\python.exe -m pytest -q

Lint:

    .\.venv\Scripts\python.exe -m ruff check .

The repository CI performs the same backend checks plus a frontend production build.
