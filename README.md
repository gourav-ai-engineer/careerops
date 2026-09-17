# CareerOps

CareerOps is a safety-first career intelligence pipeline for India-based AI/ML, GenAI, software, backend, and data opportunities, including NIT Silchar campus hiring.

## Current capabilities

- FastAPI service with a health endpoint.
- PostgreSQL/SQLAlchemy foundation for companies, jobs, contacts, and job-contact relationships.
- Public contact validation helpers.
- Professional phone metadata fields with explicit phone type, source, verification status, and confidence.
- Validation endpoint: `POST /contacts/validate`.

## Run locally

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the interactive API documentation at `http://127.0.0.1:8000/docs`.

## Contact-data safety rules

CareerOps only accepts legitimately published professional contact information, such as company switchboards, official recruitment helplines, and publicly listed work phones. It does not infer numbers, bypass logins, scrape private profiles, or store private/personal mobile numbers.

## Planned next steps

1. Add source adapters for official career pages and public company contact pages.
2. Add deduplication and evidence records for every discovered contact.
3. Add Smartsheet synchronization with dry-run previews.
4. Add scheduled discovery and monitoring.
