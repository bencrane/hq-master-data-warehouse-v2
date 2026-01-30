-- Email Ingestion: AnyMailFinder
-- Creates raw and extracted tables for AnyMailFinder email data
-- Also creates reference table for email-to-person mapping

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.email_anymailfinder (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Canonical fields (from Clay context, source of truth)
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Metadata
    workflow_slug TEXT,
    clay_table_url TEXT,

    -- The AnyMailFinder response
    anymailfinder_raw_payload JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_email_amf_domain ON raw.email_anymailfinder(domain);
CREATE INDEX IF NOT EXISTS idx_raw_email_amf_linkedin ON raw.email_anymailfinder(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_raw_email_amf_created ON raw.email_anymailfinder(created_at);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.email_anymailfinder (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.email_anymailfinder(id),

    -- Canonical fields (from top-level request, NOT from anymailfinder payload)
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Extracted from anymailfinder_raw_payload.results
    email TEXT,
    validation TEXT,                 -- 'valid', 'unknown', etc.
    alternatives TEXT[],             -- array of alternative emails
    success BOOLEAN,

    -- Extracted from anymailfinder_raw_payload.input (for reference)
    input_not_found_error BOOLEAN,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ext_email_amf_email ON extracted.email_anymailfinder(email);
CREATE INDEX IF NOT EXISTS idx_ext_email_amf_domain ON extracted.email_anymailfinder(domain);
CREATE INDEX IF NOT EXISTS idx_ext_email_amf_linkedin ON extracted.email_anymailfinder(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_ext_email_amf_validation ON extracted.email_anymailfinder(validation);

-- =============================================================================
-- REFERENCE TABLE (built as side effect of ingestion)
-- =============================================================================

-- Email to person mapping
-- Links known emails to linkedin profiles (first record wins, no overwrites)
CREATE TABLE IF NOT EXISTS reference.email_to_person (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    domain TEXT,
    company_name TEXT,
    source TEXT DEFAULT 'anymailfinder', -- which provider provided this mapping
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ref_email_person_email ON reference.email_to_person(email);
CREATE INDEX IF NOT EXISTS idx_ref_email_person_linkedin ON reference.email_to_person(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_ref_email_person_domain ON reference.email_to_person(domain);

-- =============================================================================
-- WORKFLOW REGISTRY ENTRY
-- =============================================================================

INSERT INTO reference.enrichment_workflow_registry
(workflow_slug, provider, platform, payload_type, entity_type, description)
VALUES (
  'anymailfinder-email',
  'anymailfinder',
  'clay',
  'enrichment',
  'person',
  'AnyMailFinder email lookup results for a person'
)
ON CONFLICT (workflow_slug) DO NOTHING;
