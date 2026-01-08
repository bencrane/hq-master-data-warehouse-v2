-- Migration: Company Customer Claygent Tables
-- Created: 2026-01-07
-- Purpose: Store customer research data from Claygent

-- ============================================
-- RAW TABLE: company_customer_claygent_payloads
-- ============================================
CREATE TABLE IF NOT EXISTS raw.company_customer_claygent_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Origin company identifiers
    origin_company_domain TEXT NOT NULL,
    origin_company_name TEXT,
    origin_company_linkedin_url TEXT,
    
    -- Workflow metadata
    workflow_slug TEXT NOT NULL,
    provider TEXT NOT NULL,
    platform TEXT NOT NULL,
    payload_type TEXT NOT NULL,
    
    -- Full Claygent response (includes customers[], reasoning, confidence, stepsTaken)
    raw_payload JSONB NOT NULL
);

-- Index for lookups by origin company
CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_payloads_domain 
    ON raw.company_customer_claygent_payloads(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_payloads_created 
    ON raw.company_customer_claygent_payloads(created_at DESC);

-- ============================================
-- EXTRACTED TABLE: company_customer_claygent
-- ============================================
CREATE TABLE IF NOT EXISTS extracted.company_customer_claygent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Link back to raw payload
    raw_payload_id UUID NOT NULL REFERENCES raw.company_customer_claygent_payloads(id),
    
    -- Origin company (the company whose customers we researched)
    origin_company_domain TEXT NOT NULL,
    origin_company_name TEXT,
    
    -- Customer company (exploded from customers array)
    company_customer_name TEXT NOT NULL,
    case_study_url TEXT,
    has_case_study BOOLEAN NOT NULL DEFAULT false,
    
    -- Unique constraint: one record per origin+customer pair
    UNIQUE(origin_company_domain, company_customer_name)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_origin 
    ON extracted.company_customer_claygent(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_customer 
    ON extracted.company_customer_claygent(company_customer_name);

CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_raw_payload 
    ON extracted.company_customer_claygent(raw_payload_id);

CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_has_case_study 
    ON extracted.company_customer_claygent(has_case_study) WHERE has_case_study = true;

-- ============================================
-- WORKFLOW REGISTRY ENTRY
-- ============================================
INSERT INTO reference.enrichment_workflow_registry (
    workflow_slug,
    provider,
    platform,
    payload_type,
    entity_type
) VALUES (
    'claygent-get-all-company-customers',
    'clay',
    'clay',
    'customer_research',
    'company'
) ON CONFLICT (workflow_slug) DO NOTHING;

