-- ICP Verdict tables for storing AI-generated ICP match verdicts
-- Raw payloads store the original AI response, extraction normalizes the fields

-- Raw payloads table
CREATE TABLE IF NOT EXISTS raw.icp_verdict_payloads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    origin_company_domain text NOT NULL,
    company_domain text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_icp_verdict_payloads_origin_domain 
    ON raw.icp_verdict_payloads(origin_company_domain);
CREATE INDEX IF NOT EXISTS idx_icp_verdict_payloads_company_domain 
    ON raw.icp_verdict_payloads(company_domain);

-- Extracted/normalized verdicts
CREATE TABLE IF NOT EXISTS extracted.icp_verdict (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id uuid REFERENCES raw.icp_verdict_payloads(id),
    origin_company_domain text NOT NULL,
    company_domain text NOT NULL,
    is_match boolean,
    match_reason text,
    created_at timestamptz DEFAULT now()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_icp_verdict_origin_domain 
    ON extracted.icp_verdict(origin_company_domain);
CREATE INDEX IF NOT EXISTS idx_icp_verdict_company_domain 
    ON extracted.icp_verdict(company_domain);
CREATE INDEX IF NOT EXISTS idx_icp_verdict_is_match 
    ON extracted.icp_verdict(is_match);

-- Workflow registry entry
INSERT INTO reference.enrichment_workflow_registry (workflow_slug, provider, platform, payload_type, entity_type)
VALUES ('icp-verdict-enrichment', 'clay', 'modal', 'icp_verdict', 'company')
ON CONFLICT (workflow_slug) DO NOTHING;
