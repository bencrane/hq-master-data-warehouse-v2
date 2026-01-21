-- Migration: Crunchbase Domain Inference
-- Uses Gemini 3 Flash to infer company domains from Crunchbase data

-- Raw payloads table
CREATE TABLE IF NOT EXISTS raw.crunchbase_domain_inference_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    crunchbase_url TEXT NOT NULL,
    investment_round TEXT,
    vc_name TEXT,
    vc_domain TEXT,
    workflow_slug TEXT NOT NULL,
    provider TEXT,
    platform TEXT,
    payload_type TEXT,
    raw_payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted domain inference results
CREATE TABLE IF NOT EXISTS extracted.crunchbase_domain_inference (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.crunchbase_domain_inference_payloads(id),
    company_name TEXT NOT NULL,
    crunchbase_url TEXT NOT NULL,
    inferred_domain TEXT,
    confidence TEXT,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_crunchbase_domain_inference_payloads_company_name 
    ON raw.crunchbase_domain_inference_payloads(company_name);
CREATE INDEX IF NOT EXISTS idx_crunchbase_domain_inference_payloads_crunchbase_url 
    ON raw.crunchbase_domain_inference_payloads(crunchbase_url);
CREATE INDEX IF NOT EXISTS idx_crunchbase_domain_inference_domain 
    ON extracted.crunchbase_domain_inference(inferred_domain);
CREATE INDEX IF NOT EXISTS idx_crunchbase_domain_inference_company_name 
    ON extracted.crunchbase_domain_inference(company_name);

-- Workflow registry entry
INSERT INTO reference.enrichment_workflow_registry (
    workflow_slug,
    provider,
    platform,
    payload_type,
    entity_type,
    description
) VALUES (
    'gemini-crunchbase-domain-inference',
    'google',
    'gemini',
    'domain_inference',
    'company',
    'Infer company domain from Crunchbase data using Gemini 3 Flash'
) ON CONFLICT (workflow_slug) DO NOTHING;
