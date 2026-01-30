-- Email Ingestion: LeadMagic
-- Creates raw and extracted tables for LeadMagic email data

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.email_leadmagic (
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

    -- The LeadMagic response
    leadmagic_raw_payload JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_email_lm_domain ON raw.email_leadmagic(domain);
CREATE INDEX IF NOT EXISTS idx_raw_email_lm_linkedin ON raw.email_leadmagic(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_raw_email_lm_created ON raw.email_leadmagic(created_at);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.email_leadmagic (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.email_leadmagic(id),

    -- Canonical fields (from top-level request, NOT from leadmagic payload)
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Extracted from leadmagic_raw_payload
    email TEXT,
    status TEXT,                     -- 'valid_catch_all', 'valid', 'invalid', etc.
    message TEXT,                    -- 'Email found', etc.
    has_mx BOOLEAN,
    mx_record TEXT,                  -- Primary MX record
    mx_provider TEXT,                -- 'Mimecast', etc.
    is_domain_catch_all BOOLEAN,
    employment_verified BOOLEAN,     -- Person still works there
    mx_security_gateway BOOLEAN,
    credits_consumed INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ext_email_lm_email ON extracted.email_leadmagic(email);
CREATE INDEX IF NOT EXISTS idx_ext_email_lm_domain ON extracted.email_leadmagic(domain);
CREATE INDEX IF NOT EXISTS idx_ext_email_lm_linkedin ON extracted.email_leadmagic(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_ext_email_lm_status ON extracted.email_leadmagic(status);
CREATE INDEX IF NOT EXISTS idx_ext_email_lm_employment ON extracted.email_leadmagic(employment_verified);

-- =============================================================================
-- WORKFLOW REGISTRY ENTRY
-- =============================================================================

INSERT INTO reference.enrichment_workflow_registry
(workflow_slug, provider, platform, payload_type, entity_type, description)
VALUES (
  'leadmagic-email',
  'leadmagic',
  'clay',
  'enrichment',
  'person',
  'LeadMagic email lookup results for a person'
)
ON CONFLICT (workflow_slug) DO NOTHING;
