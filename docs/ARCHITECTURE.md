# CareerOps Architecture

CareerOps is a safety-first career intelligence platform for India-based AI/ML, GenAI, software, backend, platform, and data opportunities.

## System design

```text
Sources (exports, RSS, approved APIs, manual uploads)
        |
        v
FastAPI ingestion API
        |
        v
Normalization -> validation -> deduplication
        |
        +--> Official job verification
        +--> Eligibility and skill-fit analysis
        +--> Public professional contact discovery
        +--> Resume tailoring draft generation
        |
        v
PostgreSQL (system of record)
        |
        +--> Windmill scheduled workflows
        +--> Smartsheet synchronization
        +--> Web dashboard
```

## Design principles

1. PostgreSQL is the source of truth; Smartsheet is a synchronized operational view.
2. Every job and contact retains source evidence and verification status.
3. No private/personal phone-number inference, scraping, login bypass, or unauthorized enrichment.
4. Resume changes are drafts until explicitly approved by the user.
5. Smartsheet writes support dry-run previews and idempotent upserts.
6. Provider integrations are replaceable through adapters.
7. Failures are observable, retryable, and safe to rerun.

## Core modules

- `ingestion`: receives job messages, exports, feeds, and API payloads.
- `verification`: checks official employer sources and records evidence.
- `deduplication`: uses canonical URL, normalized company/title/location, and content fingerprints.
- `scoring`: evaluates role fit against the user's profile and target preferences.
- `contact_discovery`: finds only legitimately published professional contact information.
- `resume_engine`: creates versioned, user-reviewable resume drafts.
- `smartsheet_sync`: synchronizes approved records with idempotency safeguards.
- `workflows`: scheduled and event-driven Windmill orchestration.

## Initial delivery order

1. Stabilize API configuration and database migrations.
2. Add job, source, evidence, and processing-run models.
3. Implement ingestion and deterministic deduplication.
4. Add official-source verification adapters.
5. Add Smartsheet dry-run and synchronization.
6. Add contact discovery adapters.
7. Add resume draft generation and approval workflow.
8. Add dashboard and monitoring.

## Security and compliance

- Never commit API keys or tokens.
- Use environment variables and local secret storage.
- Respect provider terms, rate limits, and privacy requirements.
- Store only publicly available professional information with source URLs.
