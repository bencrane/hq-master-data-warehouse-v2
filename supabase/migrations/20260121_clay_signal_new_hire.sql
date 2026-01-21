-- Migration: Clay Signal - New Hire
-- Description: Tables for storing Clay "New Hire" signal payloads and extracted data
-- Signal Type: Company-level
-- Required Input: domain OR company_linkedin_url
-- Output: company_name, person_linkedin_url

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_new_hire_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input fields (what was sent to Clay)
    company_domain TEXT,
    company_linkedin_url TEXT,
    
    -- Signal metadata (references reference.signal_registry)
    signal_slug TEXT NOT NULL,
    
    -- Traceability
    clay_table_url TEXT,
    
    -- Raw Clay response
    raw_payload JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT clay_new_hire_has_identifier CHECK (
        company_domain IS NOT NULL OR company_linkedin_url IS NOT NULL
    )
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_clay_new_hire_payloads_company_domain 
    ON raw.clay_new_hire_payloads(company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_new_hire_payloads_created_at 
    ON raw.clay_new_hire_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.clay_new_hire (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_new_hire_payloads(id),
    
    -- Input context (denormalized for query convenience)
    company_domain TEXT,
    company_linkedin_url TEXT,
    
    -- Extracted fields (Clay output)
    company_name TEXT,
    person_linkedin_url TEXT,
    
    -- Signal metadata
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_clay_new_hire_company_domain 
    ON extracted.clay_new_hire(company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_new_hire_person_linkedin_url 
    ON extracted.clay_new_hire(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_clay_new_hire_signal_detected_at 
    ON extracted.clay_new_hire(signal_detected_at DESC);

-- =============================================================================
-- NOTE: Signal registry entry is in 20260121_signal_registry.sql
-- Signal slug: clay-new-hire
-- =============================================================================
