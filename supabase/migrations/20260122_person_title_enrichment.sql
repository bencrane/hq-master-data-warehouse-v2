-- Migration: Person Title Enrichment Tables
-- Created: 2026-01-22
-- Purpose: Store person data with title enrichment (seniority_level, job_function, cleaned_job_title)

-- Raw table: stores incoming payloads
CREATE TABLE IF NOT EXISTS raw.person_title_enrichment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    linkedin_url TEXT NOT NULL,
    workflow_slug TEXT NOT NULL,
    raw_payload JSONB NOT NULL,
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_raw_linkedin 
    ON raw.person_title_enrichment(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_raw_workflow 
    ON raw.person_title_enrichment(workflow_slug);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_raw_clay_url 
    ON raw.person_title_enrichment(clay_table_url);

-- Extracted table: flattened person data with title enrichment
CREATE TABLE IF NOT EXISTS extracted.person_title_enrichment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.person_title_enrichment(id),
    linkedin_url TEXT NOT NULL UNIQUE,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    cleaned_first_name TEXT,
    cleaned_last_name TEXT,
    cleaned_full_name TEXT,
    -- Location fields
    location_name TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,
    has_country BOOLEAN DEFAULT FALSE,
    -- Company info
    company_domain TEXT,
    latest_company TEXT,
    -- Title fields
    latest_title TEXT,
    cleaned_job_title TEXT,
    seniority_level TEXT,
    job_function TEXT,
    latest_start_date DATE,
    -- Clay references
    clay_company_table_id TEXT,
    clay_company_record_id TEXT,
    clay_table_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_ext_linkedin 
    ON extracted.person_title_enrichment(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_ext_domain 
    ON extracted.person_title_enrichment(company_domain);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_ext_seniority 
    ON extracted.person_title_enrichment(seniority_level);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_ext_function 
    ON extracted.person_title_enrichment(job_function);
CREATE INDEX IF NOT EXISTS idx_person_title_enrich_ext_clay_url 
    ON extracted.person_title_enrichment(clay_table_url);
