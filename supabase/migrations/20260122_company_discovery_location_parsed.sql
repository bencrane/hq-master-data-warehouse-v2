-- Migration: Company Discovery Location Parsed Tables
-- Created: 2026-01-22
-- Purpose: Store company discovery data with pre-parsed location fields (Gemini parsing done in Clay)

-- Raw table: stores incoming payloads
CREATE TABLE IF NOT EXISTS raw.company_discovery_location_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_domain TEXT NOT NULL,
    workflow_slug TEXT NOT NULL,
    provider TEXT,
    platform TEXT,
    payload_type TEXT,
    raw_company_payload JSONB NOT NULL,
    raw_company_location_payload JSONB,
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_raw_domain 
    ON raw.company_discovery_location_parsed(company_domain);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_raw_workflow 
    ON raw.company_discovery_location_parsed(workflow_slug);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_raw_clay_url 
    ON raw.company_discovery_location_parsed(clay_table_url);

-- Extracted table: flattened company data with parsed location
CREATE TABLE IF NOT EXISTS extracted.company_discovery_location_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.company_discovery_location_parsed(id),
    domain TEXT NOT NULL UNIQUE,
    name TEXT,
    linkedin_url TEXT,
    linkedin_company_id BIGINT,
    clay_company_id BIGINT,
    size TEXT,
    type TEXT,
    -- Location fields
    country TEXT,
    location TEXT,
    city TEXT,
    state TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,
    -- Industry/business info
    industry TEXT,
    industries JSONB,
    description TEXT,
    annual_revenue TEXT,
    total_funding_amount_range_usd TEXT,
    resolved_domain TEXT,
    derived_datapoints JSONB,
    -- Clay reference
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_ext_domain 
    ON extracted.company_discovery_location_parsed(domain);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_ext_city 
    ON extracted.company_discovery_location_parsed(city);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_ext_state 
    ON extracted.company_discovery_location_parsed(state);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_ext_country 
    ON extracted.company_discovery_location_parsed(country);
CREATE INDEX IF NOT EXISTS idx_company_discovery_lp_ext_clay_url 
    ON extracted.company_discovery_location_parsed(clay_table_url);
