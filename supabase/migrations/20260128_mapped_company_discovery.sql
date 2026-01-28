-- Migration: Mapped Company Discovery
-- Description: Creates mapped schema and company_discovery table for derived/lookup-matched data
-- Flow: raw → extracted → mapped → core

-- =============================================================================
-- CREATE MAPPED SCHEMA
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS mapped;

-- =============================================================================
-- CREATE MAPPED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS mapped.company_discovery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to extracted record
    extracted_id UUID REFERENCES extracted.company_discovery(id),

    -- Domain (denormalized for easy querying)
    domain TEXT NOT NULL,

    -- Original values (for reference)
    original_location TEXT,
    original_industry TEXT,
    original_company_name TEXT,

    -- Matched location fields
    matched_city TEXT,
    matched_state TEXT,
    matched_country TEXT,
    location_match_source TEXT,  -- which source in location_parsed matched

    -- Matched industry
    matched_industry TEXT,

    -- Matched company name
    matched_company_name TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mapped_company_discovery_domain
    ON mapped.company_discovery(domain);

CREATE INDEX IF NOT EXISTS idx_mapped_company_discovery_extracted_id
    ON mapped.company_discovery(extracted_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mapped_company_discovery_domain_unique
    ON mapped.company_discovery(domain);

-- Update trigger
CREATE OR REPLACE FUNCTION mapped.update_company_discovery_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_mapped_company_discovery_updated_at
    BEFORE UPDATE ON mapped.company_discovery
    FOR EACH ROW
    EXECUTE FUNCTION mapped.update_company_discovery_updated_at();
