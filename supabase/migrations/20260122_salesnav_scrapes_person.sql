-- Migration: SalesNav Scrapes Person Tables
-- Created: 2026-01-22
-- Purpose: Store person data from SalesNav scrapes with AI-parsed location fields

-- Raw table: stores incoming payloads
CREATE TABLE IF NOT EXISTS raw.salesnav_scrapes_person_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_linkedin_sales_nav_url TEXT,
    linkedin_user_profile_urn TEXT,
    domain TEXT,
    raw_payload JSONB NOT NULL,
    workflow_slug TEXT NOT NULL DEFAULT 'ai-person-location-parsing',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_salesnav_person_payloads_linkedin_url 
    ON raw.salesnav_scrapes_person_payloads(person_linkedin_sales_nav_url);
CREATE INDEX IF NOT EXISTS idx_salesnav_person_payloads_domain 
    ON raw.salesnav_scrapes_person_payloads(domain);

-- Extracted table: flattened person data with parsed location
CREATE TABLE IF NOT EXISTS extracted.salesnav_scrapes_person (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.salesnav_scrapes_person_payloads(id),
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone_number TEXT,
    profile_headline TEXT,
    profile_summary TEXT,
    job_title TEXT,
    job_description TEXT,
    job_started_on TEXT,
    person_linkedin_sales_nav_url TEXT,
    linkedin_user_profile_urn TEXT,
    location_raw TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,
    has_country BOOLEAN DEFAULT FALSE,
    company_name TEXT,
    domain TEXT,
    company_linkedin_url TEXT,
    source_id UUID,
    upload_id UUID,
    notes TEXT,
    matching_filters BOOLEAN,
    source_created_at TIMESTAMPTZ,
    clay_batch_number TEXT,
    sent_to_clay_at TIMESTAMPTZ,
    export_title TEXT,
    export_timestamp TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_salesnav_person_extracted_linkedin_url 
    ON extracted.salesnav_scrapes_person(person_linkedin_sales_nav_url);
CREATE INDEX IF NOT EXISTS idx_salesnav_person_extracted_domain 
    ON extracted.salesnav_scrapes_person(domain);
CREATE INDEX IF NOT EXISTS idx_salesnav_person_extracted_city 
    ON extracted.salesnav_scrapes_person(city);
CREATE INDEX IF NOT EXISTS idx_salesnav_person_extracted_state 
    ON extracted.salesnav_scrapes_person(state);
CREATE INDEX IF NOT EXISTS idx_salesnav_person_extracted_country 
    ON extracted.salesnav_scrapes_person(country);
