# CareerOps Architecture

## End-to-end design

Sources (CSV/WhatsApp exports, approved feeds/APIs, manual inputs)
-> FastAPI ingestion
-> normalization/extraction
-> deterministic deduplication
-> official-domain screening and optional live source checking
-> explicit verification
-> requirements + candidate fit
-> public professional contact providers
-> PostgreSQL source of truth
-> Smartsheet operational view
-> Next.js dashboard
-> Windmill scheduled orchestration

## Backend boundaries

The API is split by domain: ingestion, jobs, verification, contacts, candidate profile, resume, dashboard, runs, and Smartsheet sync. External providers implement the ContactProvider contract.

## Data guarantees

- Job identity is deterministic and deduplicated.
- Verification is distinct from source screening.
- Fit assessments are explainable and tied to a candidate profile.
- Contact evidence retains provider, source URL, status, confidence, and timestamp.
- Smartsheet writes have dry-run/apply separation, changed-cell updates, and no delete path.
- Resume tailoring is draft-only and does not fabricate claims.
- Processing runs and audit events support traceability.

## Security

Credentials are environment-only. Optional API-key protection is provided by middleware. CORS is restricted to the configured frontend origin. Live source checking accepts HTTPS employer-domain URLs and blocks private/loopback targets and off-domain redirects.

## Deployment

Docker Compose provides PostgreSQL, FastAPI, and Next.js. Windmill scripts stay outside the API process so scheduling and retry policy can evolve independently.
