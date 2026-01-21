-- Migration: Case Study Extraction Tables
-- Created: 2026-01-08
-- Purpose: Store extracted case study data from Gemini 3 Flash

-- ============================================
-- RAW TABLE: case_study_extraction_payloads
-- ============================================
CREATE TABLE IF NOT EXISTS raw.case_study_extraction_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Input identifiers
    case_study_url TEXT NOT NULL,
    origin_company_domain TEXT NOT NULL,
    origin_company_name TEXT,
    company_customer_name TEXT NOT NULL,
    has_case_study_url BOOLEAN NOT NULL DEFAULT false,
    
    -- Workflow metadata
    workflow_slug TEXT NOT NULL,
    provider TEXT NOT NULL,
    platform TEXT NOT NULL,
    payload_type TEXT NOT NULL,
    
    -- Full Gemini response
    raw_payload JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_case_study_extraction_payloads_url 
    ON raw.case_study_extraction_payloads(case_study_url);

CREATE INDEX IF NOT EXISTS idx_case_study_extraction_payloads_origin 
    ON raw.case_study_extraction_payloads(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_case_study_extraction_payloads_created 
    ON raw.case_study_extraction_payloads(created_at DESC);

-- ============================================
-- EXTRACTED TABLE: case_study_details
-- ============================================
CREATE TABLE IF NOT EXISTS extracted.case_study_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Link back to raw payload
    raw_payload_id UUID NOT NULL REFERENCES raw.case_study_extraction_payloads(id),
    
    -- Case study identifiers
    case_study_url TEXT NOT NULL UNIQUE,
    
    -- Origin company (the company that published the case study)
    origin_company_domain TEXT NOT NULL,
    origin_company_name TEXT,
    
    -- Customer company (the company featured in the case study)
    company_customer_name TEXT NOT NULL,
    company_customer_domain TEXT,  -- nullable, only if hyperlinked/listed in page
    
    -- Extracted content
    article_title TEXT,
    
    -- Extraction metadata
    confidence TEXT,
    reasoning TEXT
);

CREATE INDEX IF NOT EXISTS idx_case_study_details_origin 
    ON extracted.case_study_details(origin_company_domain);

CREATE INDEX IF NOT EXISTS idx_case_study_details_customer_domain 
    ON extracted.case_study_details(company_customer_domain) 
    WHERE company_customer_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_case_study_details_raw_payload 
    ON extracted.case_study_details(raw_payload_id);

CREATE INDEX IF NOT EXISTS idx_case_study_details_confidence 
    ON extracted.case_study_details(confidence);

-- ============================================
-- EXTRACTED TABLE: case_study_champions
-- ============================================
CREATE TABLE IF NOT EXISTS extracted.case_study_champions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Link to parent case study
    case_study_id UUID NOT NULL REFERENCES extracted.case_study_details(id) ON DELETE CASCADE,
    
    -- Champion details
    full_name TEXT NOT NULL,
    job_title TEXT,
    company_name TEXT
);

CREATE INDEX IF NOT EXISTS idx_case_study_champions_case_study 
    ON extracted.case_study_champions(case_study_id);

CREATE INDEX IF NOT EXISTS idx_case_study_champions_name 
    ON extracted.case_study_champions(full_name);

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
    'gemini-extract-case-study-details',
    'google',
    'gemini',
    'case_study_extraction',
    'company'
) ON CONFLICT (workflow_slug) DO NOTHING;

