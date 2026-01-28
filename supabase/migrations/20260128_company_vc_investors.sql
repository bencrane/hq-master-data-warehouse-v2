-- Migration: Company VC Investors
-- Description: Tables for storing company VC investor data from Clay
-- Input: company with up to 12 VC co-investors
-- Output: Exploded rows - one per VC investor

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.company_vc_investors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company fields
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_linkedin_url TEXT,

    -- Origin VC (the VC whose portfolio we're analyzing)
    vc_og TEXT,

    -- Co-investors (up to 12)
    vc_1 TEXT,
    vc_2 TEXT,
    vc_3 TEXT,
    vc_4 TEXT,
    vc_5 TEXT,
    vc_6 TEXT,
    vc_7 TEXT,
    vc_8 TEXT,
    vc_9 TEXT,
    vc_10 TEXT,
    vc_11 TEXT,
    vc_12 TEXT,

    -- Workflow metadata
    workflow_slug TEXT,

    -- Raw payload
    raw_payload JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_raw_company_name
    ON raw.company_vc_investors(company_name);
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_raw_vc_og
    ON raw.company_vc_investors(vc_og);
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_raw_created_at
    ON raw.company_vc_investors(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.company_vc_investors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.company_vc_investors(id),

    -- Company fields (denormalized)
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_linkedin_url TEXT,

    -- Origin VC
    vc_og TEXT,

    -- The exploded VC name (one row per VC)
    vc_name TEXT NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_ext_company_name
    ON extracted.company_vc_investors(company_name);
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_ext_vc_og
    ON extracted.company_vc_investors(vc_og);
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_ext_vc_name
    ON extracted.company_vc_investors(vc_name);
CREATE INDEX IF NOT EXISTS idx_company_vc_investors_ext_created_at
    ON extracted.company_vc_investors(created_at DESC);

-- =============================================================================
-- WORKFLOW REGISTRY ENTRY
-- =============================================================================

INSERT INTO reference.enrichment_workflow_registry
(workflow_slug, provider, platform, payload_type, entity_type, description)
VALUES (
  'clay-company-vc-investors',
  'clay',
  'clay',
  'enrichment',
  'company',
  'Company VC investor data from Clay portfolio research'
)
ON CONFLICT (workflow_slug) DO NOTHING;
