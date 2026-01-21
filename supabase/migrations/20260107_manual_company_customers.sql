-- Manual company customers table
-- For pre-flattened data that doesn't need raw payload storage or extraction

CREATE SCHEMA IF NOT EXISTS manual;

CREATE TABLE manual.company_customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Origin company (the company whose customers these are)
    origin_company_domain TEXT NOT NULL,
    origin_company_name TEXT,
    origin_company_linkedin_url TEXT,
    
    -- The customer
    company_customer_name TEXT NOT NULL,
    company_customer_domain TEXT,
    company_customer_linkedin_url TEXT,
    
    -- Optional metadata
    case_study_url TEXT,
    has_case_study BOOLEAN,  -- nullable, no assumption
    source_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicates, allow upsert
    UNIQUE(origin_company_domain, company_customer_name)
);

-- Indexes
CREATE INDEX idx_manual_company_customers_origin_domain ON manual.company_customers(origin_company_domain);
CREATE INDEX idx_manual_company_customers_customer_domain ON manual.company_customers(company_customer_domain);
CREATE INDEX idx_manual_company_customers_created ON manual.company_customers(created_at DESC);

