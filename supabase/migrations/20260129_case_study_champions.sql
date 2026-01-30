-- Case Study Buyers: stores extracted buyer/champion data from case studies (v2)

-- Raw table: stores the full payload from extract_case_study_buyer
CREATE TABLE raw.case_study_buyers_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_company_name TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,
    customer_company_name TEXT,
    customer_company_domain TEXT,
    case_study_url TEXT,
    raw_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted table: one row per person (buyer) quoted in case study
CREATE TABLE extracted.case_study_buyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.case_study_buyers_payloads(id),
    -- Origin company (publisher)
    origin_company_name TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,
    -- Customer company (featured)
    customer_company_name TEXT,
    customer_company_domain TEXT,
    case_study_url TEXT,
    -- Buyer (person quoted)
    buyer_full_name TEXT NOT NULL,
    buyer_job_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_case_study_buyers_origin_domain ON extracted.case_study_buyers(origin_company_domain);
CREATE INDEX idx_case_study_buyers_customer_domain ON extracted.case_study_buyers(customer_company_domain);
CREATE INDEX idx_case_study_buyers_full_name ON extracted.case_study_buyers(buyer_full_name);

COMMENT ON TABLE raw.case_study_buyers_payloads IS 'Raw payloads from extract_case_study_buyer Gemini extraction';
COMMENT ON TABLE extracted.case_study_buyers IS 'Flattened buyers (people quoted) from case studies - one row per person';
