# CareerOps Workflow Specification

## Job processing workflow

1. Ingest a source payload or uploaded export.
2. Parse candidate job records into a typed schema.
3. Normalize company, title, location, employment type, and URLs.
4. Compute a deterministic fingerprint and check PostgreSQL for duplicates.
5. Run conservative official-source screening.
6. Persist the source evidence and screening result.
7. Require an explicit verification decision before marking a job verified or rejected.
8. Evaluate eligibility and role fit with transparent evidence.
9. Persist the job, source evidence, and processing run.
10. Produce a dry-run Smartsheet change preview.
11. Synchronize only approved and verified records.

### Verification rules

- A matching company domain or subdomain is **screened**, not automatically considered proof of ownership.
- A `verified` decision is an explicit operator confirmation after official-domain screening.
- A `rejected` decision is recorded as evidence and transitions the job through the status state machine.
- Jobs without a usable application/source URL remain unverified and require review.
- Verification evidence includes the source URL, evidence type, status, reason, and timestamp.

## Contact workflow

1. Resolve the employer domain from a verified job.
2. Query configured providers through adapters.
3. Prefer official recruiting/campus contacts and public professional work details.
4. Store provider, source URL, verification status, confidence, and retrieval time.
5. Never infer, scrape, or store private/personal phone numbers.

## Resume workflow

1. User selects a saved job.
2. Extract requirements and keywords from the verified description.
3. Compare requirements with the master resume and project inventory.
4. Generate a versioned draft with change explanations.
5. Require explicit user approval before export or replacement.

## Reliability requirements

- Idempotent job and Smartsheet synchronization.
- Exponential backoff for transient provider failures.
- Per-provider rate limiting and timeout controls.
- Structured logs with correlation IDs.
- Dead-letter or failed-run records for manual review.
- No automatic application submission.
