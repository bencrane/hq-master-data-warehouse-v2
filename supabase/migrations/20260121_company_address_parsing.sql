-- Migration: Company Address Parsing (SalesNav Scrapes)
-- Description: Tables for storing company records with AI-parsed address components
-- Purpose: Backlog processing - parse "Company registered address" into city/state/country
-- Flow: raw (original input) -> AI (Gemini) -> extracted (parsed output)

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.salesnav_scrapes_company_address_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Company identifiers (as provided, not normalized)
    company_name TEXT,
    linkedin_url TEXT,
    linkedin_urn TEXT,
    domain TEXT,
    
    -- Original payload
    raw_payload JSONB NOT NULL,
    
    -- Workflow metadata
    workflow_slug TEXT NOT NULL DEFAULT 'ai-company-address-parsing',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_payloads_domain 
    ON raw.salesnav_scrapes_company_address_payloads(domain);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_payloads_linkedin_url 
    ON raw.salesnav_scrapes_company_address_payloads(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_payloads_created_at 
    ON raw.salesnav_scrapes_company_address_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.salesnav_scrapes_company_address (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.salesnav_scrapes_company_address_payloads(id),
    
    -- Company identifiers (as provided)
    company_name TEXT,
    linkedin_url TEXT,
    linkedin_urn TEXT,
    domain TEXT,
    
    -- Original company data
    description TEXT,
    headcount INTEGER,
    industries TEXT,
    
    -- Original address (raw string)
    registered_address_raw TEXT,
    
    -- AI-parsed address components
    city TEXT,
    state TEXT,
    country TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,
    has_country BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_domain 
    ON extracted.salesnav_scrapes_company_address(domain);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_linkedin_url 
    ON extracted.salesnav_scrapes_company_address(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_country 
    ON extracted.salesnav_scrapes_company_address(country);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_state 
    ON extracted.salesnav_scrapes_company_address(state);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_city 
    ON extracted.salesnav_scrapes_company_address(city);
CREATE INDEX IF NOT EXISTS idx_salesnav_scrapes_company_address_created_at 
    ON extracted.salesnav_scrapes_company_address(created_at DESC);
