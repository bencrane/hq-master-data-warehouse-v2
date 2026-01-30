-- ICP Primary Fit Criterion Migration
-- Stores primary fit criterion for ICP evaluation

-- ============================================================================
-- RAW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw.icp_fit_criterion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Raw payload from AI
    raw_payload JSONB NOT NULL,

    -- Metadata
    workflow_slug TEXT DEFAULT 'icp-fit-criterion',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_icp_fit_criterion_domain ON raw.icp_fit_criterion(domain);
CREATE INDEX IF NOT EXISTS idx_raw_icp_fit_criterion_created ON raw.icp_fit_criterion(created_at DESC);

-- ============================================================================
-- EXTRACTED TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS extracted.icp_fit_criterion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.icp_fit_criterion(id),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Extracted from payload
    reasoning TEXT,

    -- Primary fit criterion fields
    primary_criterion TEXT,           -- Main fit criterion statement
    criterion_type TEXT,              -- Type/category of criterion
    qualifying_signals JSONB,         -- Array of qualifying signals
    disqualifying_signals JSONB,      -- Array of disqualifying signals
    ideal_company_attributes JSONB,   -- Array of ideal company attributes
    minimum_requirements JSONB,       -- Array of minimum requirements

    -- Token/cost metadata from source AI
    source_tokens_used INTEGER,
    source_input_tokens INTEGER,
    source_output_tokens INTEGER,
    source_cost TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain)  -- One fit criterion record per company
);

CREATE INDEX IF NOT EXISTS idx_extracted_icp_fit_criterion_domain ON extracted.icp_fit_criterion(domain);
CREATE INDEX IF NOT EXISTS idx_extracted_icp_fit_criterion_raw_payload ON extracted.icp_fit_criterion(raw_payload_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON raw.icp_fit_criterion TO authenticated;
GRANT SELECT, INSERT, UPDATE ON extracted.icp_fit_criterion TO authenticated;
GRANT SELECT ON raw.icp_fit_criterion TO anon;
GRANT SELECT ON extracted.icp_fit_criterion TO anon;
