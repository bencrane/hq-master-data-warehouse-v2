-- Migration: Clay Signal - Job Posting
-- Description: Tables for storing Clay "Job Posting" signal payloads and extracted data
-- Signal Type: Company-level
-- Required Input: company_linkedin_url
-- Flattened Output: company_name, job_title, location, company_domain, job_linkedin_url, post_on

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_job_posting_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input fields
    company_linkedin_url TEXT NOT NULL,
    
    -- Signal metadata (references reference.signal_registry)
    signal_slug TEXT NOT NULL,
    
    -- Traceability
    clay_table_url TEXT,
    
    -- Company record payload (stored as-is)
    company_record_raw_payload JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_payloads_company_linkedin_url 
    ON raw.clay_job_posting_payloads(company_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_payloads_created_at 
    ON raw.clay_job_posting_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.clay_job_posting (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_job_posting_payloads(id),
    
    -- Input context (denormalized for query convenience)
    company_linkedin_url TEXT NOT NULL,
    
    -- Extracted fields (flattened from Clay output)
    company_name TEXT,
    job_title TEXT,
    location TEXT,
    company_domain TEXT,
    job_linkedin_url TEXT,
    post_on DATE,
    
    -- Signal metadata
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_company_linkedin_url 
    ON extracted.clay_job_posting(company_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_company_domain 
    ON extracted.clay_job_posting(company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_job_title 
    ON extracted.clay_job_posting(job_title);
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_post_on 
    ON extracted.clay_job_posting(post_on DESC);
CREATE INDEX IF NOT EXISTS idx_clay_job_posting_signal_detected_at 
    ON extracted.clay_job_posting(signal_detected_at DESC);

-- =============================================================================
-- NOTE: Signal registry entry is in 20260121_signal_registry.sql
-- Signal slug: clay-job-posting
-- =============================================================================
