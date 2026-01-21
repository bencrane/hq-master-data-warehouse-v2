-- Migration: Clay Signal - Job Change
-- Description: Tables for storing Clay "Job Change" signal payloads and extracted data
-- Signal Type: Person-level
-- Required Input: person_linkedin_profile_url
-- Output: confidence, previous_company, new_company_*, start_date_at_new_job, started_role_last_3_months, person_linkedin_profile

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_job_change_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input fields
    person_linkedin_profile_url TEXT NOT NULL,
    
    -- Signal metadata (references reference.signal_registry)
    signal_slug TEXT NOT NULL,
    
    -- Traceability
    clay_table_url TEXT,
    
    -- Full Clay job change event payload (origin, confidence, newCompany, fullProfile, etc.)
    job_change_event_raw_payload JSONB,
    
    -- Person record payload
    person_record_raw_payload JSONB,
    
    -- Flattened fields payload (stored as-is)
    raw_event_payload JSONB,
    
    -- Threshold setting (e.g. 90 for 3 months)
    lookback_threshold_days INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_clay_job_change_payloads_person_linkedin 
    ON raw.clay_job_change_payloads(person_linkedin_profile_url);
CREATE INDEX IF NOT EXISTS idx_clay_job_change_payloads_created_at 
    ON raw.clay_job_change_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.clay_job_change (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_job_change_payloads(id),
    
    -- Input context (denormalized for query convenience)
    person_linkedin_profile_url TEXT NOT NULL,
    
    -- Extracted fields (flattened from Clay output)
    confidence TEXT,
    previous_company_domain TEXT,
    previous_company_linkedin_url TEXT,
    new_company_name TEXT,
    new_company_domain TEXT,
    new_company_linkedin_url TEXT,
    start_date_at_new_job DATE,
    started_within_threshold BOOLEAN,
    lookback_threshold_days INTEGER,
    
    -- Signal metadata
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_clay_job_change_person_linkedin 
    ON extracted.clay_job_change(person_linkedin_profile_url);
CREATE INDEX IF NOT EXISTS idx_clay_job_change_new_company_domain 
    ON extracted.clay_job_change(new_company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_job_change_previous_company_domain 
    ON extracted.clay_job_change(previous_company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_job_change_confidence 
    ON extracted.clay_job_change(confidence);
CREATE INDEX IF NOT EXISTS idx_clay_job_change_signal_detected_at 
    ON extracted.clay_job_change(signal_detected_at DESC);
