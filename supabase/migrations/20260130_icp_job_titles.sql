-- ICP Job Titles Migration
-- Stores target ICP job titles for companies with camelCase normalization

-- ============================================================================
-- RAW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw.icp_job_titles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Raw payload from AI
    raw_payload JSONB NOT NULL,

    -- Metadata
    workflow_slug TEXT DEFAULT 'icp-job-titles',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_icp_job_titles_domain ON raw.icp_job_titles(domain);
CREATE INDEX IF NOT EXISTS idx_raw_icp_job_titles_created ON raw.icp_job_titles(created_at DESC);

-- ============================================================================
-- EXTRACTED TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS extracted.icp_job_titles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.icp_job_titles(id),

    -- Company context
    company_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    company_linkedin_url TEXT,

    -- Extracted from payload
    reasoning TEXT,

    -- Raw titles (camelCase as received)
    raw_primary_titles JSONB,
    raw_influencer_titles JSONB,
    raw_extended_titles JSONB,

    -- Normalized titles (human-readable)
    primary_titles JSONB,      -- ["Chief Information Security Officer", "VP of Security", ...]
    influencer_titles JSONB,   -- ["Security Manager", "Compliance Manager", ...]
    extended_titles JSONB,     -- ["Security Analyst", "Compliance Analyst", ...]

    -- Token/cost metadata from source AI
    source_tokens_used INTEGER,
    source_input_tokens INTEGER,
    source_output_tokens INTEGER,
    source_cost TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain)  -- One ICP job titles record per company
);

CREATE INDEX IF NOT EXISTS idx_extracted_icp_job_titles_domain ON extracted.icp_job_titles(domain);
CREATE INDEX IF NOT EXISTS idx_extracted_icp_job_titles_raw_payload ON extracted.icp_job_titles(raw_payload_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON raw.icp_job_titles TO authenticated;
GRANT SELECT, INSERT, UPDATE ON extracted.icp_job_titles TO authenticated;
GRANT SELECT ON raw.icp_job_titles TO anon;
GRANT SELECT ON extracted.icp_job_titles TO anon;
