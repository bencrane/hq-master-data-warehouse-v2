-- Migration: Parallel ICP Job Titles — Claude-Normalized
-- Created: 2026-02-25
-- Purpose: Store Claude Haiku-normalized ICP titles extracted from raw Parallel.ai output
-- Source: extract_icp_titles Modal function

CREATE SCHEMA IF NOT EXISTS extracted;

CREATE TABLE IF NOT EXISTS extracted.parallel_icp_job_titles_normalized (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company context
    company_domain TEXT NOT NULL,
    company_name TEXT,

    -- Source reference (raw row that was normalized)
    raw_parallel_icp_id UUID REFERENCES raw.parallel_icp_job_titles(id),

    -- Normalized titles (array of {title, buyer_role, reasoning})
    titles JSONB NOT NULL DEFAULT '[]'::jsonb,
    title_count INTEGER NOT NULL DEFAULT 0,

    -- Counts by buyer role
    champion_count INTEGER NOT NULL DEFAULT 0,
    evaluator_count INTEGER NOT NULL DEFAULT 0,
    decision_maker_count INTEGER NOT NULL DEFAULT 0,

    -- Claude usage / cost
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd NUMERIC(10, 6),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(company_domain)
);

CREATE INDEX IF NOT EXISTS idx_norm_icp_titles_domain
    ON extracted.parallel_icp_job_titles_normalized(company_domain);
CREATE INDEX IF NOT EXISTS idx_norm_icp_titles_raw_id
    ON extracted.parallel_icp_job_titles_normalized(raw_parallel_icp_id);
CREATE INDEX IF NOT EXISTS idx_norm_icp_titles_gin
    ON extracted.parallel_icp_job_titles_normalized USING GIN (titles);

-- Permissions
GRANT SELECT, INSERT, UPDATE ON extracted.parallel_icp_job_titles_normalized TO authenticated;
GRANT SELECT ON extracted.parallel_icp_job_titles_normalized TO anon;
GRANT ALL ON extracted.parallel_icp_job_titles_normalized TO service_role;
