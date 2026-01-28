-- Migration: Cleaned Apollo Tables

-- =============================================================================
-- CLEANED PEOPLE TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_people_cleaned (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Person identifiers
    linkedin_url TEXT,
    apollo_person_url TEXT,
    photo_url TEXT,

    -- Original data
    full_name TEXT,
    job_title TEXT,
    company_name TEXT,
    person_location TEXT,

    -- Cleaned data
    cleaned_first_name TEXT,
    cleaned_last_name TEXT,
    cleaned_full_name TEXT,
    cleaned_job_title TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_people_cleaned_linkedin_url
ON extracted.apollo_people_cleaned(linkedin_url);

CREATE INDEX IF NOT EXISTS idx_apollo_people_cleaned_created_at
ON extracted.apollo_people_cleaned(created_at DESC);

-- =============================================================================
-- CLEANED COMPANIES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.apollo_companies_cleaned (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    apollo_company_url TEXT,
    company_name TEXT,
    company_headcount TEXT,
    industry TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apollo_companies_cleaned_apollo_url
ON extracted.apollo_companies_cleaned(apollo_company_url);

CREATE INDEX IF NOT EXISTS idx_apollo_companies_cleaned_created_at
ON extracted.apollo_companies_cleaned(created_at DESC);
