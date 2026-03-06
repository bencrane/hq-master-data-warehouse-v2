-- Migration: parallel_person_gtm_briefs
-- Description: Person-level GTM brief tables for Parallel AI enrichment
-- Note: No unique constraint on person_linkedin_url — allows re-runs

-- Raw table for storing Parallel AI responses
CREATE TABLE IF NOT EXISTS raw.parallel_person_gtm_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_linkedin_url TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,
    lead_current_company_domain TEXT,
    lead_past_company_domain TEXT,
    run_id TEXT,
    raw_payload JSONB NOT NULL,
    success BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    enrichment_slug TEXT DEFAULT 'alumni_person_gtm_brief_unstructured_output',
    cost_usd NUMERIC(10, 6) DEFAULT 0.10,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_person_gtm_briefs_linkedin
    ON raw.parallel_person_gtm_briefs(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_raw_person_gtm_briefs_run_id
    ON raw.parallel_person_gtm_briefs(run_id);

CREATE INDEX IF NOT EXISTS idx_raw_person_gtm_briefs_created
    ON raw.parallel_person_gtm_briefs(created_at DESC);

COMMENT ON TABLE raw.parallel_person_gtm_briefs IS 'Raw payloads from Parallel AI person-level GTM brief enrichment';

-- Extracted table for structured results
CREATE TABLE IF NOT EXISTS extracted.parallel_person_gtm_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.parallel_person_gtm_briefs(id),
    person_linkedin_url TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,
    lead_full_name TEXT,
    lead_current_company_domain TEXT,
    lead_past_company_domain TEXT,
    run_id TEXT,
    output JSONB,
    enrichment_slug TEXT DEFAULT 'alumni_person_gtm_brief_unstructured_output',
    cost_usd NUMERIC(10, 6) DEFAULT 0.10,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_person_gtm_briefs_linkedin
    ON extracted.parallel_person_gtm_briefs(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_extracted_person_gtm_briefs_origin
    ON extracted.parallel_person_gtm_briefs(origin_company_domain);

COMMENT ON TABLE extracted.parallel_person_gtm_briefs IS 'Extracted person-level GTM briefs from Parallel AI enrichment';

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION extracted.update_parallel_person_gtm_briefs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_parallel_person_gtm_briefs_updated_at ON extracted.parallel_person_gtm_briefs;
CREATE TRIGGER trigger_parallel_person_gtm_briefs_updated_at
    BEFORE UPDATE ON extracted.parallel_person_gtm_briefs
    FOR EACH ROW
    EXECUTE FUNCTION extracted.update_parallel_person_gtm_briefs_updated_at();
