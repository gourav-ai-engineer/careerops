# CareerOps Production Runbook

## 1. Start the platform

Copy .env.example to .env. Configure PostgreSQL and any optional Smartsheet, Hunter, or API-key secrets. Start Docker Compose and verify /health and /health/db.

## 2. First data pass

Ingest a CSV or WhatsApp export. The pipeline extracts, normalizes, deduplicates, and persists jobs. For important jobs, screen the official employer domain and use the live check when appropriate. Make an explicit verification decision before treating the job as verified.

## 3. Fit and contacts

Recalculate fit for verified/later-stage jobs. Discover only public professional contacts from approved providers. Review source evidence and confidence before using contact data operationally.

## 4. Smartsheet

PostgreSQL is the system of record. Use the Smartsheet dry-run endpoints before apply. Synchronization writes changed cells only and never deletes rows.

## 5. Resume workflow

Save the master resume, generate a job-specific draft, review its change plan and matched/missing keywords, then explicitly approve or reject it. Draft generation never overwrites the master and never invents facts.

## 6. Windmill

Schedule the scripts in windmill/ for ingestion, fit recalculation, contact discovery, and Smartsheet synchronization. Keep provider retry behavior within provider limits.

## 7. Security

Keep .env and credentials out of Git. Use HTTPS for live checks and public business sources. Do not scrape private profiles, infer personal numbers, bypass authentication, or auto-submit applications.

## 8. Recovery

Inspect /runs, request IDs, audit events, and provider evidence when diagnosing failures. Re-run idempotent workflows after transient failures rather than manually duplicating records.
