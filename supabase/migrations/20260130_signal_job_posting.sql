-- Signal: Job Posting
-- Tables for storing job posting signals from Clay
-- Includes client_domain for multi-tenant signal tracking

--------------------------------------------------------------------------------
-- RAW TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.signal_job_posting_payloads (
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

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_raw_client
    ON raw.signal_job_posting_payloads(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_raw_created
    ON raw.signal_job_posting_payloads(created_at);

COMMENT ON TABLE raw.signal_job_posting_payloads IS 'Raw payloads for job posting signals';

--------------------------------------------------------------------------------
-- EXTRACTED TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS extracted.signal_job_posting (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to raw
    raw_payload_id UUID REFERENCES raw.signal_job_posting_payloads(id),

    -- Client tracking
    client_domain TEXT NOT NULL,

    -- Company info
    company_domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,
    company_linkedin_id BIGINT,

    -- Job info
    job_title TEXT,
    normalized_title TEXT,
    seniority TEXT,
    employment_type TEXT,
    location TEXT,

    -- Job posting details
    job_linkedin_url TEXT,
    job_linkedin_id BIGINT,
    posted_at TIMESTAMPTZ,

    -- Salary info
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT,
    salary_unit TEXT,

    -- Recruiter info (stored but not primary use case)
    recruiter_name TEXT,
    recruiter_linkedin_url TEXT,

    -- Signal metadata
    is_initial_check BOOLEAN DEFAULT FALSE,
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_client
    ON extracted.signal_job_posting(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_company_domain
    ON extracted.signal_job_posting(company_domain);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_job_title
    ON extracted.signal_job_posting(normalized_title);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_seniority
    ON extracted.signal_job_posting(seniority);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_posted_at
    ON extracted.signal_job_posting(posted_at);

CREATE INDEX IF NOT EXISTS idx_signal_job_posting_detected_at
    ON extracted.signal_job_posting(signal_detected_at);

COMMENT ON TABLE extracted.signal_job_posting IS 'Extracted job posting signals with normalized fields';
