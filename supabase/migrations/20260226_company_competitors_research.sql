-- Company competitors research table
-- Stores AI-generated competitor analysis for companies

CREATE TABLE core.company_competitors_research (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_name TEXT NOT NULL,
  company_description TEXT,
  domain TEXT NOT NULL,
  notes TEXT,
  response TEXT,
  reasoning TEXT,
  confidence TEXT,
  steps_taken TEXT[],
  top_competitors JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT company_competitors_research_domain_key UNIQUE (domain)
);

-- Index on domain for lookups
CREATE INDEX idx_company_competitors_research_domain
ON core.company_competitors_research(domain);

-- Grant permissions
GRANT ALL ON core.company_competitors_research TO service_role;
GRANT SELECT ON core.company_competitors_research TO anon;
