-- ICP Core Value Proposition Migration
-- Stores target ICP core value proposition for companies

-- ============================================================================
-- RAW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw.icp_value_proposition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Raw payload from AI
    raw_payload JSONB NOT NULL,

    -- Metadata
    workflow_slug TEXT DEFAULT 'icp-value-proposition',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_icp_value_proposition_domain ON raw.icp_value_proposition(domain);
CREATE INDEX IF NOT EXISTS idx_raw_icp_value_proposition_created ON raw.icp_value_proposition(created_at DESC);

-- ============================================================================
-- EXTRACTED TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS extracted.icp_value_proposition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.icp_value_proposition(id),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Extracted from payload
    reasoning TEXT,

    -- Core value proposition fields
    value_proposition TEXT,           -- Main value proposition statement
    key_benefits JSONB,               -- Array of key benefits
    target_market TEXT,               -- Target market description
    differentiators JSONB,            -- Array of differentiators
    pain_points_addressed JSONB,      -- Array of pain points addressed

    -- Token/cost metadata from source AI
    source_tokens_used INTEGER,
    source_input_tokens INTEGER,
    source_output_tokens INTEGER,
    source_cost TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain)  -- One value proposition record per company
);

CREATE INDEX IF NOT EXISTS idx_extracted_icp_value_proposition_domain ON extracted.icp_value_proposition(domain);
CREATE INDEX IF NOT EXISTS idx_extracted_icp_value_proposition_raw_payload ON extracted.icp_value_proposition(raw_payload_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON raw.icp_value_proposition TO authenticated;
GRANT SELECT, INSERT, UPDATE ON extracted.icp_value_proposition TO authenticated;
GRANT SELECT ON raw.icp_value_proposition TO anon;
GRANT SELECT ON extracted.icp_value_proposition TO anon;
