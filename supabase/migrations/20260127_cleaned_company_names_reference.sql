-- Migration: Cleaned Company Names Reference
-- Description: Tables for storing Clay-cleaned company names (canonical name reference)
-- Purpose: Avoid messy names like "WUNDERGROUND LLC" → use "Wunderground" instead
-- Input: original_company_name, domain, cleaned_company_name (from Clay)

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_cleaned_company_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Input fields (what was sent from Clay)
    domain TEXT NOT NULL,
    original_company_name TEXT,
    cleaned_company_name TEXT,

    -- Raw payload if we want to store extra data later
    raw_payload JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_clay_cleaned_company_names_domain
    ON raw.clay_cleaned_company_names(domain);
CREATE INDEX IF NOT EXISTS idx_clay_cleaned_company_names_created_at
    ON raw.clay_cleaned_company_names(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE (Canonical Reference)
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.cleaned_company_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_cleaned_company_names(id),

    -- Domain is the unique key (one canonical name per domain)
    domain TEXT NOT NULL UNIQUE,

    -- The messy original name
    original_company_name TEXT,

    -- The canonical cleaned name (what we use in core.companies)
    cleaned_company_name TEXT,

    -- Source tracking
    source TEXT DEFAULT 'clay',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_cleaned_company_names_original
    ON extracted.cleaned_company_names(original_company_name);
CREATE INDEX IF NOT EXISTS idx_cleaned_company_names_cleaned
    ON extracted.cleaned_company_names(cleaned_company_name);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION extracted.update_cleaned_company_names_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_cleaned_company_names_updated_at ON extracted.cleaned_company_names;
CREATE TRIGGER tr_cleaned_company_names_updated_at
    BEFORE UPDATE ON extracted.cleaned_company_names
    FOR EACH ROW
    EXECUTE FUNCTION extracted.update_cleaned_company_names_updated_at();

-- =============================================================================
-- NOTES
-- =============================================================================
-- Usage:
--   1. Clay sends records with domain + original_company_name + cleaned_company_name
--   2. Modal endpoint stores in raw table, then upserts to extracted table
--   3. When building core.companies view or updating names, join on domain
--
-- Future: May replace Clay cleaning with AI-based cleaning
