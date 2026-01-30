-- Migration: Mapped Case Study Champions
-- Description: Creates mapped.case_study_champions for job title enrichment
-- Flow: extracted → core → mapped (with lookup enrichment)

-- =============================================================================
-- CREATE MAPPED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS mapped.case_study_champions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to core record
    core_champion_id UUID REFERENCES core.case_study_champions(id),

    -- Denormalized fields for easy querying
    full_name TEXT NOT NULL,
    company_domain TEXT,
    origin_company_domain TEXT,

    -- Original job title (for reference)
    original_job_title TEXT,

    -- Matched job title fields (from reference.job_title_lookup)
    matched_cleaned_job_title TEXT,
    matched_seniority TEXT,
    matched_job_function TEXT,
    job_title_match_source TEXT,

    -- Future enrichment: location
    matched_city TEXT,
    matched_state TEXT,
    matched_country TEXT,
    location_match_source TEXT,

    -- Future enrichment: linkedin
    linkedin_url TEXT,
    core_person_id UUID REFERENCES core.people(id),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint
    CONSTRAINT mapped_champions_core_id_unique UNIQUE (core_champion_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mapped_champions_company_domain
    ON mapped.case_study_champions(company_domain);

CREATE INDEX IF NOT EXISTS idx_mapped_champions_origin_domain
    ON mapped.case_study_champions(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_mapped_champions_job_function
    ON mapped.case_study_champions(matched_job_function);

CREATE INDEX IF NOT EXISTS idx_mapped_champions_seniority
    ON mapped.case_study_champions(matched_seniority);

CREATE INDEX IF NOT EXISTS idx_mapped_champions_linkedin_url
    ON mapped.case_study_champions(linkedin_url);

-- Update trigger
CREATE OR REPLACE FUNCTION mapped.update_case_study_champions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_mapped_case_study_champions_updated_at
    BEFORE UPDATE ON mapped.case_study_champions
    FOR EACH ROW
    EXECUTE FUNCTION mapped.update_case_study_champions_updated_at();

-- Comments
COMMENT ON TABLE mapped.case_study_champions IS 'Case study champions with job title lookup enrichment';
COMMENT ON COLUMN mapped.case_study_champions.original_job_title IS 'Raw job title from case study extraction';
COMMENT ON COLUMN mapped.case_study_champions.matched_cleaned_job_title IS 'Normalized job title from reference.job_title_lookup';
COMMENT ON COLUMN mapped.case_study_champions.matched_job_function IS 'Job function (e.g., Operations, Engineering) from lookup';
COMMENT ON COLUMN mapped.case_study_champions.matched_seniority IS 'Seniority level (e.g., Director, VP) from lookup';
