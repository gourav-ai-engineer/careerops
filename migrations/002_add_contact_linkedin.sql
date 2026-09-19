-- CareerOps schema migration 002
-- Adds the public professional LinkedIn field used by contact sync.
ALTER TABLE contacts ADD COLUMN IF NOT EXISTS linkedin_url TEXT;
