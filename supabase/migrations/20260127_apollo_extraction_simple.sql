-- Migration: Apollo Extraction Tables (Simple - No Deduplication)
-- Each record stays tied to its scrape_settings_id
-- Dedupe at query time with DISTINCT ON (linkedin_url) when needed

-- =============================================================================
-- DROP OLD TABLES (junction-based approach)
-- =============================================================================

DROP TABLE IF EXISTS extracted.apollo_person_matches CASCADE;
DROP TABLE IF EXISTS extracted.apollo_company_matches CASCADE;
DROP TABLE IF EXISTS extracted.apollo_people CASCADE;
DROP TABLE IF EXISTS extracted.apollo_companies CASCADE;

-- =============================================================================
-- SIMPLE PEOPLE TABLE (one row per raw record)
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_instantdata_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to search that found this person
    scrape_settings_id UUID NOT NULL REFERENCES public.apollo_instantdata_scrape_settings(id),
    raw_record_id UUID,

    -- Person data
    linkedin_url TEXT,
    full_name TEXT,
    job_title TEXT,
    person_location TEXT,
    photo_url TEXT,
    apollo_person_url TEXT,

    -- Company data (denormalized)
    company_name TEXT,
    company_headcount TEXT,
    industry TEXT,
    apollo_company_url TEXT,

    -- Source tracking
    source_created_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_people_settings_id
ON extracted.apollo_instantdata_people(scrape_settings_id);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_people_linkedin_url
ON extracted.apollo_instantdata_people(linkedin_url);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_people_created_at
ON extracted.apollo_instantdata_people(created_at DESC);

-- =============================================================================
-- SIMPLE COMPANIES TABLE (one row per raw record)
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_instantdata_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to search that found this company
    scrape_settings_id UUID NOT NULL REFERENCES public.apollo_instantdata_scrape_settings(id),
    raw_record_id UUID,

    -- Company data
    apollo_company_url TEXT,
    company_name TEXT,
    company_headcount TEXT,
    industry TEXT,

    -- Source tracking
    source_created_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_companies_settings_id
ON extracted.apollo_instantdata_companies(scrape_settings_id);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_companies_apollo_url
ON extracted.apollo_instantdata_companies(apollo_company_url);

CREATE INDEX IF NOT EXISTS idx_apollo_instantdata_companies_created_at
ON extracted.apollo_instantdata_companies(created_at DESC);

-- =============================================================================
-- HELPER VIEWS FOR DEDUPED ACCESS
-- =============================================================================

-- Latest person data per linkedin_url
CREATE OR REPLACE VIEW extracted.apollo_people_deduped AS
SELECT DISTINCT ON (linkedin_url)
    id,
    linkedin_url,
    full_name,
    job_title,
    person_location,
    photo_url,
    apollo_person_url,
    company_name,
    company_headcount,
    industry,
    apollo_company_url,
    created_at
FROM extracted.apollo_instantdata_people
WHERE linkedin_url IS NOT NULL
ORDER BY linkedin_url, created_at DESC;

-- Latest company data per apollo_company_url
CREATE OR REPLACE VIEW extracted.apollo_companies_deduped AS
SELECT DISTINCT ON (apollo_company_url)
    id,
    apollo_company_url,
    company_name,
    company_headcount,
    industry,
    created_at
FROM extracted.apollo_instantdata_companies
WHERE apollo_company_url IS NOT NULL
ORDER BY apollo_company_url, created_at DESC;
