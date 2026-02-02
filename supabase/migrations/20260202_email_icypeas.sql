-- Migration: Icypeas Email Tables
-- Created: 2026-02-02
-- Purpose: Store Icypeas email lookup results

-- =============================================================================
-- RAW TABLE: email_icypeas
-- =============================================================================
CREATE TABLE IF NOT EXISTS raw.email_icypeas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Person identifiers (from Clay context)
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,

    -- Company identifiers
    domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Workflow metadata
    workflow_slug TEXT NOT NULL DEFAULT 'icypeas-email',
    clay_table_url TEXT,

    -- Full Icypeas response
    icypeas_raw_payload JSONB NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_email_icypeas_raw_person_linkedin
    ON raw.email_icypeas(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_email_icypeas_raw_domain
    ON raw.email_icypeas(domain);

CREATE INDEX IF NOT EXISTS idx_email_icypeas_raw_created
    ON raw.email_icypeas(created_at DESC);


-- =============================================================================
-- EXTRACTED TABLE: email_icypeas
-- =============================================================================
CREATE TABLE IF NOT EXISTS extracted.email_icypeas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Link to raw
    raw_payload_id UUID NOT NULL REFERENCES raw.email_icypeas(id),

    -- Person identifiers
    person_linkedin_url TEXT,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,

    -- Company identifiers
    domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Extracted email data
    email TEXT,
    status TEXT,  -- FOUND, NOT_FOUND, etc.
    success BOOLEAN,
    search_id TEXT,
    certainty TEXT,  -- ultra_sure, sure, etc.
    mx_records JSONB,  -- array of mx records
    mx_provider TEXT,  -- google, microsoft, etc.
    emails JSONB  -- full emails array from response
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_icypeas_extracted_person_linkedin
    ON extracted.email_icypeas(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_email_icypeas_extracted_email
    ON extracted.email_icypeas(email);

CREATE INDEX IF NOT EXISTS idx_email_icypeas_extracted_domain
    ON extracted.email_icypeas(domain);

CREATE INDEX IF NOT EXISTS idx_email_icypeas_extracted_raw_payload
    ON extracted.email_icypeas(raw_payload_id);


-- =============================================================================
-- WORKFLOW REGISTRY ENTRY
-- =============================================================================
INSERT INTO reference.enrichment_workflow_registry
(workflow_slug, provider, platform, payload_type, entity_type, description, workflow_type, raw_table, extracted_table, is_active)
VALUES (
    'icypeas-email',
    'icypeas',
    'clay',
    'enrichment',
    'person',
    'Icypeas email lookup results for a person',
    'ingest',
    'raw.email_icypeas',
    'extracted.email_icypeas',
    true
)
ON CONFLICT (workflow_slug) DO NOTHING;
