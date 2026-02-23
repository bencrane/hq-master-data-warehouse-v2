-- Migration: Parallel AI Case Study Tables
-- Created: 2026-02-16
-- Purpose: Store case study extractions from Parallel AI (24K+ payloads from Clay)

-- ============================================
-- RAW TABLE: parallel_case_study_payloads
-- ============================================
CREATE TABLE IF NOT EXISTS raw.parallel_case_study_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Key identifiers (denormalized for querying)
    case_study_url TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,

    -- Optional metadata
    clay_table_url TEXT,

    -- Full Parallel AI response
    payload JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_parallel_case_study_payloads_url
    ON raw.parallel_case_study_payloads(case_study_url);

CREATE INDEX IF NOT EXISTS idx_parallel_case_study_payloads_origin
    ON raw.parallel_case_study_payloads(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_parallel_case_study_payloads_created
    ON raw.parallel_case_study_payloads(created_at DESC);


-- ============================================
-- EXTRACTED TABLE: parallel_case_studies
-- ============================================
CREATE TABLE IF NOT EXISTS extracted.parallel_case_studies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to raw
    raw_payload_id UUID REFERENCES raw.parallel_case_study_payloads(id),

    -- Case study URL (unique per case study)
    case_study_url TEXT NOT NULL,

    -- Origin/publisher company
    origin_company_domain TEXT NOT NULL,
    publishing_company_name TEXT,

    -- Customer/featured company
    customer_company_name TEXT,
    customer_company_domain TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One row per case study URL
    CONSTRAINT uq_parallel_case_studies_url UNIQUE (case_study_url)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_parallel_case_studies_origin
    ON extracted.parallel_case_studies(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_parallel_case_studies_customer_domain
    ON extracted.parallel_case_studies(customer_company_domain)
    WHERE customer_company_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_parallel_case_studies_raw_payload
    ON extracted.parallel_case_studies(raw_payload_id);


-- ============================================
-- EXTRACTED TABLE: parallel_case_study_champions
-- ============================================
CREATE TABLE IF NOT EXISTS extracted.parallel_case_study_champions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to parent case study
    case_study_id UUID REFERENCES extracted.parallel_case_studies(id) ON DELETE CASCADE,

    -- Denormalized for easier querying
    customer_company_domain TEXT,
    origin_company_domain TEXT,

    -- Champion details
    full_name TEXT NOT NULL,
    job_title TEXT,
    testimonial TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_parallel_case_study_champions_case_study
    ON extracted.parallel_case_study_champions(case_study_id);

CREATE INDEX IF NOT EXISTS idx_parallel_case_study_champions_customer_domain
    ON extracted.parallel_case_study_champions(customer_company_domain)
    WHERE customer_company_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_parallel_case_study_champions_name
    ON extracted.parallel_case_study_champions(full_name);

-- Full text search on testimonials (useful for 24K records)
CREATE INDEX IF NOT EXISTS idx_parallel_case_study_champions_testimonial_gin
    ON extracted.parallel_case_study_champions USING gin(to_tsvector('english', testimonial))
    WHERE testimonial IS NOT NULL;


-- ============================================
-- FUNCTION: Populate core.company_names from case studies
-- ============================================
-- This function upserts company names for both origin and customer companies

CREATE OR REPLACE FUNCTION extracted.populate_company_names_from_case_study()
RETURNS TRIGGER AS $$
BEGIN
    -- Upsert origin company (publisher) into core.company_names
    IF NEW.origin_company_domain IS NOT NULL THEN
        INSERT INTO core.company_names (domain, source, raw_name, updated_at)
        VALUES (NEW.origin_company_domain, 'parallel-case-study', NEW.publishing_company_name, NOW())
        ON CONFLICT (domain, source) DO UPDATE SET
            raw_name = COALESCE(EXCLUDED.raw_name, core.company_names.raw_name),
            updated_at = NOW();

        -- Also upsert into core.companies
        INSERT INTO core.companies (domain, name, updated_at)
        VALUES (NEW.origin_company_domain, NEW.publishing_company_name, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            name = COALESCE(core.companies.name, EXCLUDED.name),
            updated_at = NOW();
    END IF;

    -- Upsert customer company (featured) into core.company_names
    IF NEW.customer_company_domain IS NOT NULL THEN
        INSERT INTO core.company_names (domain, source, raw_name, updated_at)
        VALUES (NEW.customer_company_domain, 'parallel-case-study', NEW.customer_company_name, NOW())
        ON CONFLICT (domain, source) DO UPDATE SET
            raw_name = COALESCE(EXCLUDED.raw_name, core.company_names.raw_name),
            updated_at = NOW();

        -- Also upsert into core.companies
        INSERT INTO core.companies (domain, name, updated_at)
        VALUES (NEW.customer_company_domain, NEW.customer_company_name, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            name = COALESCE(core.companies.name, EXCLUDED.name),
            updated_at = NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-populate core.company_names on insert
CREATE TRIGGER tr_parallel_case_studies_populate_company_names
    AFTER INSERT ON extracted.parallel_case_studies
    FOR EACH ROW
    EXECUTE FUNCTION extracted.populate_company_names_from_case_study();


-- ============================================
-- COMMENTS
-- ============================================
COMMENT ON TABLE raw.parallel_case_study_payloads IS 'Raw payloads from Parallel AI case study extraction via Clay';
COMMENT ON TABLE extracted.parallel_case_studies IS 'Extracted case study metadata - one row per case study URL';
COMMENT ON TABLE extracted.parallel_case_study_champions IS 'Champions (people quoted) from case studies - one row per person';
COMMENT ON FUNCTION extracted.populate_company_names_from_case_study IS 'Auto-populates core.company_names when case studies are inserted';
