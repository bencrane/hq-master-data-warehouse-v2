-- Migration: Clay Signal - Promotion
-- Description: Tables for storing Clay "Promotion" signal payloads and extracted data
-- Signal Type: Person-level
-- Required Input: person_linkedin_url
-- Output: confidence, previous_title, new_title, start_date_with_new_title

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_promotion_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input fields
    person_linkedin_profile_url TEXT NOT NULL,
    
    -- Signal metadata (references reference.signal_registry)
    signal_slug TEXT NOT NULL,
    
    -- Traceability
    clay_table_url TEXT,
    
    -- Full Clay promotion event payload (origin, newTitle, fullProfile, previousTitle, etc.)
    promotion_event_raw_payload JSONB,
    
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
CREATE INDEX IF NOT EXISTS idx_clay_promotion_payloads_person_linkedin 
    ON raw.clay_promotion_payloads(person_linkedin_profile_url);
CREATE INDEX IF NOT EXISTS idx_clay_promotion_payloads_created_at 
    ON raw.clay_promotion_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.clay_promotion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_promotion_payloads(id),
    
    -- Input context (denormalized for query convenience)
    person_linkedin_profile_url TEXT NOT NULL,
    
    -- Extracted fields (flattened from Clay output)
    confidence TEXT,
    previous_title TEXT,
    new_title TEXT,
    start_date_with_new_title DATE,
    
    -- Threshold fields
    lookback_threshold_days INTEGER,
    started_within_threshold BOOLEAN,
    
    -- Signal metadata
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_clay_promotion_person_linkedin 
    ON extracted.clay_promotion(person_linkedin_profile_url);
CREATE INDEX IF NOT EXISTS idx_clay_promotion_new_title 
    ON extracted.clay_promotion(new_title);
CREATE INDEX IF NOT EXISTS idx_clay_promotion_signal_detected_at 
    ON extracted.clay_promotion(signal_detected_at DESC);
