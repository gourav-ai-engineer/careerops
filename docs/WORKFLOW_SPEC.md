# CareerOps Workflow Specification

## Job processing workflow

1. Ingest a source payload or uploaded export.
2. Parse candidate job records into a typed schema.
3. Normalize company, title, location, employment type, and URLs.
4. Compute a deterministic fingerprint and check PostgreSQL for duplicates.
5. Verify the opportunity against an official employer or application source.
6. Evaluate eligibility and role fit with transparent evidence.
7. Persist the job, source evidence, and processing run.
8. Produce a dry-run Smartsheet change preview.
9. Synchronize only approved and verified records.

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
