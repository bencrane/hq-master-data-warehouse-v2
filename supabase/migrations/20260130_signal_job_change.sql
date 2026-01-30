-- Signal: Job Change
-- Tables for storing job change signals (person moves to new company)
-- Includes client_domain for multi-tenant signal tracking

--------------------------------------------------------------------------------
-- RAW TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.signal_job_change_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Client tracking
    client_domain TEXT NOT NULL,

    -- Origin tracking (from Clay)
    origin_table_id TEXT,
    origin_record_id TEXT,

    -- Full payload storage
    raw_payload JSONB NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_raw_client
    ON raw.signal_job_change_payloads(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_raw_created
    ON raw.signal_job_change_payloads(created_at);

COMMENT ON TABLE raw.signal_job_change_payloads IS 'Raw payloads for job change signals';

--------------------------------------------------------------------------------
-- EXTRACTED TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS extracted.signal_job_change (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to raw
    raw_payload_id UUID REFERENCES raw.signal_job_change_payloads(id),

    -- Client tracking
    client_domain TEXT NOT NULL,

    -- Person info
    person_name TEXT,
    person_first_name TEXT,
    person_last_name TEXT,
    person_linkedin_url TEXT,
    person_linkedin_slug TEXT,
    person_title TEXT,
    person_headline TEXT,
    person_location TEXT,
    person_country TEXT,

    -- New company info (current job)
    new_company_domain TEXT,
    new_company_name TEXT,
    new_company_linkedin_url TEXT,
    new_job_title TEXT,
    new_job_start_date DATE,
    new_job_location TEXT,

    -- Previous company info
    previous_company_linkedin_url TEXT,

    -- Confidence
    confidence INTEGER,
    reduced_confidence_reasons JSONB,

    -- Signal metadata
    is_initial_check BOOLEAN DEFAULT FALSE,
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_client
    ON extracted.signal_job_change(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_person_linkedin
    ON extracted.signal_job_change(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_new_company_domain
    ON extracted.signal_job_change(new_company_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_new_job_start
    ON extracted.signal_job_change(new_job_start_date);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_confidence
    ON extracted.signal_job_change(confidence);

CREATE INDEX IF NOT EXISTS idx_signal_job_change_detected_at
    ON extracted.signal_job_change(signal_detected_at);

COMMENT ON TABLE extracted.signal_job_change IS 'Extracted job change signals with normalized fields';
