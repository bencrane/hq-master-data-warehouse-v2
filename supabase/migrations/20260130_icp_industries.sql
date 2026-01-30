-- ICP Industries Migration
-- Stores target ICP industries for companies with AI matching to canonical industries

-- ============================================================================
-- RAW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw.icp_industries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Raw payload from AI
    raw_payload JSONB NOT NULL,

    -- Metadata
    workflow_slug TEXT DEFAULT 'icp-industries',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_icp_industries_domain ON raw.icp_industries(domain);
CREATE INDEX IF NOT EXISTS idx_raw_icp_industries_created ON raw.icp_industries(created_at DESC);

-- ============================================================================
-- EXTRACTED TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS extracted.icp_industries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.icp_industries(id),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Extracted from payload
    reasoning TEXT,
    raw_industries JSONB,  -- Original array: ["technology", "financialServices", ...]

    -- AI-matched canonical industries
    matched_industries JSONB,  -- Array of matched canonical industry names

    -- Token/cost metadata
    source_tokens_used INTEGER,
    source_input_tokens INTEGER,
    source_output_tokens INTEGER,
    source_cost TEXT,

    -- Matching metadata
    matching_model TEXT,  -- e.g., "gpt-4o-mini"
    matching_tokens_used INTEGER,
    matching_cost TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain)  -- One ICP industries record per company
);

CREATE INDEX IF NOT EXISTS idx_extracted_icp_industries_domain ON extracted.icp_industries(domain);
CREATE INDEX IF NOT EXISTS idx_extracted_icp_industries_raw_payload ON extracted.icp_industries(raw_payload_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON raw.icp_industries TO authenticated;
GRANT SELECT, INSERT, UPDATE ON extracted.icp_industries TO authenticated;
GRANT SELECT ON raw.icp_industries TO anon;
GRANT SELECT ON extracted.icp_industries TO anon;
