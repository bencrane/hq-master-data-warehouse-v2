-- Migration: Unified Job Title Lookup
-- Description: Consolidates job title parsing lookup tables into one
-- NOTE: Original tables are NOT deleted - this is additive only

-- =============================================================================
-- CREATE UNIFIED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS reference.job_title_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The raw job title (exact match lookup)
    raw_job_title TEXT NOT NULL,

    -- Source table this came from
    source TEXT NOT NULL,

    -- Parsed components
    cleaned_job_title TEXT,
    seniority TEXT,
    job_function TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for exact match lookups
CREATE INDEX IF NOT EXISTS idx_job_title_parsed_raw
    ON reference.job_title_parsed(raw_job_title);

-- Index for source filtering
CREATE INDEX IF NOT EXISTS idx_job_title_parsed_source
    ON reference.job_title_parsed(source);

-- Composite index for exact match by source
CREATE INDEX IF NOT EXISTS idx_job_title_parsed_raw_source
    ON reference.job_title_parsed(raw_job_title, source);

-- =============================================================================
-- INSERT FROM SOURCE TABLES
-- =============================================================================

-- 1. job_title_lookup (25,678 rows)
INSERT INTO reference.job_title_parsed (raw_job_title, source, cleaned_job_title, seniority, job_function)
SELECT
    latest_title,
    'job-title-lookup',
    cleaned_job_title,
    seniority_level,
    job_function
FROM reference.job_title_lookup;

-- 2. salesnav_people_job_title_lookup (31 rows)
INSERT INTO reference.job_title_parsed (raw_job_title, source, cleaned_job_title, seniority, job_function)
SELECT
    job_title_raw,
    'salesnav-job-title',
    job_title_cleaned,
    seniority,
    job_function
FROM reference.salesnav_people_job_title_lookup;
