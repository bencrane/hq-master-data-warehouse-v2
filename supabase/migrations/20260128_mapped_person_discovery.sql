-- Migration: Mapped Person Discovery
-- Description: Creates mapped.person_discovery table for derived/lookup-matched data
-- Flow: raw → extracted → mapped → core

-- =============================================================================
-- CREATE MAPPED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS mapped.person_discovery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to extracted record
    extracted_id UUID REFERENCES extracted.person_discovery(id),

    -- LinkedIn URL (denormalized for easy querying)
    linkedin_url TEXT NOT NULL,

    -- Original values (for reference)
    original_location TEXT,
    original_job_title TEXT,

    -- Matched location fields
    matched_city TEXT,
    matched_state TEXT,
    matched_country TEXT,
    location_match_source TEXT,

    -- Matched job title fields
    matched_cleaned_job_title TEXT,
    matched_seniority TEXT,
    matched_job_function TEXT,
    job_title_match_source TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint for upsert
    CONSTRAINT person_discovery_linkedin_url_unique UNIQUE (linkedin_url)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mapped_person_discovery_linkedin_url
    ON mapped.person_discovery(linkedin_url);

CREATE INDEX IF NOT EXISTS idx_mapped_person_discovery_extracted_id
    ON mapped.person_discovery(extracted_id);

-- Update trigger
CREATE OR REPLACE FUNCTION mapped.update_person_discovery_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_mapped_person_discovery_updated_at
    BEFORE UPDATE ON mapped.person_discovery
    FOR EACH ROW
    EXECUTE FUNCTION mapped.update_person_discovery_updated_at();
