-- Core Company Revenue Table
-- Stores annual revenue ranges from extracted.company_discovery
-- Domain is the unique key

CREATE TABLE IF NOT EXISTS core.company_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL UNIQUE,
    annual_revenue TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_company_revenue_domain ON core.company_revenue(domain);

-- Grant permissions
GRANT SELECT ON core.company_revenue TO anon, authenticated;
GRANT ALL ON core.company_revenue TO service_role;
