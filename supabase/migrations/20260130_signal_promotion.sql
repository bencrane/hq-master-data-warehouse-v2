-- Signal: Promotion
-- Tables for storing promotion signals (person title change within same company)
-- Includes client_domain for multi-tenant signal tracking

--------------------------------------------------------------------------------
-- RAW TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.signal_promotion_payloads (
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

CREATE INDEX IF NOT EXISTS idx_signal_promotion_raw_client
    ON raw.signal_promotion_payloads(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_raw_created
    ON raw.signal_promotion_payloads(created_at);

COMMENT ON TABLE raw.signal_promotion_payloads IS 'Raw payloads for promotion signals';

--------------------------------------------------------------------------------
-- EXTRACTED TABLE
--------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS extracted.signal_promotion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to raw
    raw_payload_id UUID REFERENCES raw.signal_promotion_payloads(id),

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

    -- Company info (same company - it's a promotion)
    company_domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,

    -- Promotion info
    new_title TEXT,
    previous_title TEXT,
    new_role_start_date DATE,

    -- Confidence
    confidence INTEGER,
    reduced_confidence_reasons JSONB,

    -- Signal metadata
    is_initial_check BOOLEAN DEFAULT FALSE,
    days_since_promotion INTEGER,
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_client
    ON extracted.signal_promotion(client_domain);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_person_linkedin
    ON extracted.signal_promotion(person_linkedin_url);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_company_domain
    ON extracted.signal_promotion(company_domain);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_new_role_start
    ON extracted.signal_promotion(new_role_start_date);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_confidence
    ON extracted.signal_promotion(confidence);

CREATE INDEX IF NOT EXISTS idx_signal_promotion_detected_at
    ON extracted.signal_promotion(signal_detected_at);

COMMENT ON TABLE extracted.signal_promotion IS 'Extracted promotion signals with normalized fields';
