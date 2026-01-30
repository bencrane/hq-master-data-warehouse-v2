-- Company LinkedIn URLs dimension table
-- Quick lookup of linkedin_url by domain without querying full core.companies

CREATE TABLE core.company_linkedin_urls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL UNIQUE,
    linkedin_url TEXT,
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_company_linkedin_urls_domain ON core.company_linkedin_urls(domain);
CREATE INDEX idx_company_linkedin_urls_linkedin_url ON core.company_linkedin_urls(linkedin_url);

COMMENT ON TABLE core.company_linkedin_urls IS 'Company LinkedIn URLs - quick lookup by domain';
