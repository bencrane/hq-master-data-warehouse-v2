-- Migration: Apollo Extraction Tables
-- Description: Extracted tables for Apollo instant-data-scraper data
-- Dedup keys: Companies by apollo_company_url, People by linkedin_url
-- Junction tables preserve which searches/signals matched each record

-- =============================================================================
-- EXTRACTED COMPANIES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dedup key
    apollo_company_url TEXT NOT NULL UNIQUE,

    -- Company data
    company_name TEXT,
    company_headcount TEXT,
    industry TEXT,

    -- Tracking
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_companies_company_name
ON extracted.apollo_companies(company_name);

CREATE INDEX IF NOT EXISTS idx_apollo_companies_industry
ON extracted.apollo_companies(industry);

CREATE INDEX IF NOT EXISTS idx_apollo_companies_last_seen_at
ON extracted.apollo_companies(last_seen_at DESC);

-- =============================================================================
-- EXTRACTED PEOPLE TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dedup key
    linkedin_url TEXT NOT NULL UNIQUE,

    -- Link to company
    company_id UUID REFERENCES extracted.apollo_companies(id),

    -- Person data
    full_name TEXT,
    job_title TEXT,
    person_location TEXT,
    photo_url TEXT,
    apollo_person_url TEXT,

    -- Tracking
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_people_company_id
ON extracted.apollo_people(company_id);

CREATE INDEX IF NOT EXISTS idx_apollo_people_full_name
ON extracted.apollo_people(full_name);

CREATE INDEX IF NOT EXISTS idx_apollo_people_job_title
ON extracted.apollo_people(job_title);

CREATE INDEX IF NOT EXISTS idx_apollo_people_last_seen_at
ON extracted.apollo_people(last_seen_at DESC);

-- =============================================================================
-- JUNCTION TABLES (preserve search/signal associations)
-- =============================================================================

-- Tracks which searches matched each person
CREATE TABLE IF NOT EXISTS extracted.apollo_person_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES extracted.apollo_people(id),
    scrape_settings_id UUID NOT NULL REFERENCES public.apollo_instantdata_scrape_settings(id),
    raw_record_id UUID REFERENCES raw.apollo_instantdata_scrapes(id),
    matched_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate matches for same person + search
    CONSTRAINT apollo_person_matches_unique UNIQUE (person_id, scrape_settings_id)
);

CREATE INDEX IF NOT EXISTS idx_apollo_person_matches_person_id
ON extracted.apollo_person_matches(person_id);

CREATE INDEX IF NOT EXISTS idx_apollo_person_matches_settings_id
ON extracted.apollo_person_matches(scrape_settings_id);

CREATE INDEX IF NOT EXISTS idx_apollo_person_matches_matched_at
ON extracted.apollo_person_matches(matched_at DESC);

-- Tracks which searches matched each company
CREATE TABLE IF NOT EXISTS extracted.apollo_company_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES extracted.apollo_companies(id),
    scrape_settings_id UUID NOT NULL REFERENCES public.apollo_instantdata_scrape_settings(id),
    raw_record_id UUID REFERENCES raw.apollo_instantdata_scrapes(id),
    matched_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate matches for same company + search
    CONSTRAINT apollo_company_matches_unique UNIQUE (company_id, scrape_settings_id)
);

CREATE INDEX IF NOT EXISTS idx_apollo_company_matches_company_id
ON extracted.apollo_company_matches(company_id);

CREATE INDEX IF NOT EXISTS idx_apollo_company_matches_settings_id
ON extracted.apollo_company_matches(scrape_settings_id);

CREATE INDEX IF NOT EXISTS idx_apollo_company_matches_matched_at
ON extracted.apollo_company_matches(matched_at DESC);

-- =============================================================================
-- UPDATED_AT TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION extracted.update_apollo_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_apollo_companies_updated_at ON extracted.apollo_companies;
CREATE TRIGGER tr_apollo_companies_updated_at
    BEFORE UPDATE ON extracted.apollo_companies
    FOR EACH ROW
    EXECUTE FUNCTION extracted.update_apollo_updated_at();

DROP TRIGGER IF EXISTS tr_apollo_people_updated_at ON extracted.apollo_people;
CREATE TRIGGER tr_apollo_people_updated_at
    BEFORE UPDATE ON extracted.apollo_people
    FOR EACH ROW
    EXECUTE FUNCTION extracted.update_apollo_updated_at();
