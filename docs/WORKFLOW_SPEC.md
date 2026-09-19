# CareerOps Workflow Specification

## Job workflow

1. Ingest a CSV, WhatsApp export, feed, or manual payload.
2. Extract and normalize job records.
3. Deduplicate against PostgreSQL.
4. Screen the official employer domain.
5. Optionally live-check the official HTTPS source.
6. Require an explicit verification decision.
7. Persist requirements and calculate candidate fit.
8. Discover public professional contacts.
9. Persist provider evidence and job-contact links.
10. Build a Smartsheet dry-run plan.
11. Apply the reviewed plan.
12. Generate a reviewable resume draft when needed.

## Contact workflow

Providers share one adapter contract. Official-site discovery handles public business phone numbers. The optional Hunter adapter accepts source-backed professional email records and ignores inferred or personal phone data. Provider calls use timeouts, retries, and rate limiting.

## Resume workflow

The user stores a master resume. CareerOps generates a job-specific draft with matched and missing keywords plus a change plan. The master is never overwritten by draft generation.

## Reliability and safety

- PostgreSQL is authoritative.
- Smartsheet is synchronized and never used as the source of truth.
- Dry-run exists before external writes.
- Request IDs and processing runs support troubleshooting.
- Contact merges are explicit.
- No automatic application submission.
- No private-profile scraping, authentication bypass, personal-number inference, or fabricated resume claims.

## Scheduled workflows

Windmill scripts cover source ingestion, fit recalculation, contact discovery, Smartsheet dry-run/apply, and a combined daily pipeline.
