-- Migration: rapidapi_linkedin_people
-- Description: Tables for RapidAPI LinkedIn people search extraction

-- Raw table for storing RapidAPI responses
CREATE TABLE IF NOT EXISTS raw.rapidapi_linkedin_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_domain TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    cost_usd NUMERIC(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for lookups by domain
CREATE INDEX IF NOT EXISTS idx_rapidapi_linkedin_people_domain
    ON raw.rapidapi_linkedin_people(company_domain);

-- Index for recent payloads
CREATE INDEX IF NOT EXISTS idx_rapidapi_linkedin_people_created
    ON raw.rapidapi_linkedin_people(created_at DESC);

COMMENT ON TABLE raw.rapidapi_linkedin_people IS 'Raw payloads from RapidAPI LinkedIn people search';

-- Extracted table for individual people
CREATE TABLE IF NOT EXISTS extracted.rapidapi_linkedin_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_id UUID REFERENCES raw.rapidapi_linkedin_people(id),
    company_domain TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    geo_region TEXT,
    linkedin_url TEXT,
    linkedin_urn TEXT,
    profile_picture_url TEXT,
    summary TEXT,
    open_link BOOLEAN,
    current_position JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for lookups by domain
CREATE INDEX IF NOT EXISTS idx_extracted_rapidapi_linkedin_people_domain
    ON extracted.rapidapi_linkedin_people(company_domain);

-- Index for lookups by linkedin_urn (unique person identifier)
CREATE INDEX IF NOT EXISTS idx_extracted_rapidapi_linkedin_people_urn
    ON extracted.rapidapi_linkedin_people(linkedin_urn);

-- Index for lookups by raw_id
CREATE INDEX IF NOT EXISTS idx_extracted_rapidapi_linkedin_people_raw_id
    ON extracted.rapidapi_linkedin_people(raw_id);

COMMENT ON TABLE extracted.rapidapi_linkedin_people IS 'Extracted LinkedIn people from RapidAPI search results';
