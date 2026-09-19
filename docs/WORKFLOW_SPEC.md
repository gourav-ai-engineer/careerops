# CareerOps Workflow Specification

## Job processing workflow

1. Ingest a source payload or uploaded export.
2. Parse candidate job records into a typed schema.
3. Normalize company, title, location, employment type, and URLs.
4. Compute a deterministic fingerprint and check PostgreSQL for duplicates.
5. Run conservative official-source screening.
6. Persist the source evidence and screening result.
7. Require an explicit verification decision before marking a job verified or rejected.
8. Persist extracted job requirements, including required skills and extraction metadata.
9. Evaluate eligibility, role fit, location fit, and skill fit against the candidate profile.
10. Persist a transparent fit assessment in PostgreSQL.
11. Discover legitimate public professional contacts through replaceable provider adapters.
12. Persist contact source evidence, provider, verification state, and confidence.
13. Build a dry-run Smartsheet synchronization plan for jobs and contacts.
14. Synchronize only verified and later-stage jobs after preview review.
15. Keep PostgreSQL as the system of record and Smartsheet as an operational view.

### Smartsheet job synchronization rules

- Sync is explicitly split into dry-run planning and apply operations.
- The current job tracker mapping targets Company, Role, Location, Eligibility, Fit Score, Application Status, Apply Link, Source, and Last Checked.
- Existing rows are matched by normalized company + role + application link; when the application link is blank on one side, a unique company + role fallback is allowed.
- Only changed cells are sent in update operations.
- New rows are appended to the bottom of the target sheet.
- Jobs in pre-verification states are excluded from synchronization.
- No delete operation is performed by the sync engine.
- Credentials are read from environment configuration and never stored in source control.

### Smartsheet contact synchronization rules

- Contact sync updates existing job rows; it does not create a second job row when the corresponding job row is missing.
- The current mapping uses Recruiter / Contact, Recruiter LinkedIn, and Recruiter Verification.
- Only linked contacts with source_checked or verified status are eligible.
- The contact cell can contain public professional email and phone details only when already present in the PostgreSQL contact record with its professional phone type metadata.
- LinkedIn values are copied only from the explicit linkedin_url field; they are never inferred from a name.
- Contact updates are planned before being applied, and only changed contact cells are sent.
- No delete operation is performed by contact sync.

### Verification rules

- A matching company domain or subdomain is screened, not automatically considered proof of ownership.
- A verified decision is an explicit operator confirmation after official-domain screening.
- A rejected decision is recorded as evidence and transitions the job through the status state machine.
- Jobs without a usable application/source URL remain unverified and require review.
- Verification evidence includes the source URL, evidence type, status, reason, and timestamp.

### Candidate fit rules

- Fit assessment is deterministic and explainable in rule_based_v1.
- Skill coverage contributes up to 50 points.
- Role-family match contributes up to 20 points.
- Location match contributes up to 15 points.
- Eligibility match contributes up to 15 points.
- Unknown dimensions receive partial credit rather than being silently treated as mismatches.
- Required skills come from the persisted job-requirements record when available.
- Fit assessments are keyed by job and candidate profile so reruns update the same assessment instead of creating duplicates.

### Contact discovery rules

- Providers implement a common adapter contract and can be added without changing the persistence layer.
- The current provider reads only public business contact data from HTTPS pages on the supplied company domain or its subdomains.
- Provider results are persisted with source URL, provider name, verification status, confidence, and timestamp.
- Discovery does not infer phone numbers, bypass authentication, scrape private profiles, or classify personal numbers as recruiting contacts.
- A discovered contact may optionally be linked to the originating job through the job-contact relationship.

## Contact workflow

1. Resolve the employer domain from a verified job.
2. Build a discovery context containing company, domain, source URLs, and optional role keywords.
3. Run configured provider adapters.
4. Validate and persist each discovered professional contact.
5. Persist evidence for every provider result.
6. Optionally associate contacts with the originating job.
7. Allow later providers to be added without changing the API contract.

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
