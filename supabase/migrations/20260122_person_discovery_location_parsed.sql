-- Migration: Person Discovery Location Parsed Tables
-- Created: 2026-01-22
-- Purpose: Store person discovery data with pre-parsed location fields (Gemini parsing done in Clay)

-- Raw table: stores incoming payloads
CREATE TABLE IF NOT EXISTS raw.person_discovery_location_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    linkedin_url TEXT NOT NULL,
    workflow_slug TEXT NOT NULL,
    provider TEXT,
    platform TEXT,
    payload_type TEXT,
    raw_person_payload JSONB NOT NULL,
    raw_person_parsed_location_payload JSONB,
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_person_discovery_location_parsed_linkedin_url 
    ON raw.person_discovery_location_parsed(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_person_discovery_location_parsed_workflow_slug 
    ON raw.person_discovery_location_parsed(workflow_slug);
CREATE INDEX IF NOT EXISTS idx_person_discovery_location_parsed_clay_table_url 
    ON raw.person_discovery_location_parsed(clay_table_url);

-- Extracted table: flattened person data with parsed location
CREATE TABLE IF NOT EXISTS extracted.person_discovery_location_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.person_discovery_location_parsed(id),
    linkedin_url TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    -- Raw location (original string)
    location_name TEXT,
    -- Parsed location fields
    city TEXT,
    state TEXT,
    country TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,
    has_country BOOLEAN DEFAULT FALSE,
    -- Company/job info
    company_domain TEXT,
    latest_title TEXT,
    latest_company TEXT,
    latest_start_date DATE,
    -- Clay references
    clay_company_table_id TEXT,
    clay_company_record_id TEXT,
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_extracted_person_discovery_lp_city 
    ON extracted.person_discovery_location_parsed(city);
CREATE INDEX IF NOT EXISTS idx_extracted_person_discovery_lp_state 
    ON extracted.person_discovery_location_parsed(state);
CREATE INDEX IF NOT EXISTS idx_extracted_person_discovery_lp_country 
    ON extracted.person_discovery_location_parsed(country);
CREATE INDEX IF NOT EXISTS idx_extracted_person_discovery_lp_company_domain 
    ON extracted.person_discovery_location_parsed(company_domain);
CREATE INDEX IF NOT EXISTS idx_extracted_person_discovery_lp_clay_table_url 
    ON extracted.person_discovery_location_parsed(clay_table_url);
