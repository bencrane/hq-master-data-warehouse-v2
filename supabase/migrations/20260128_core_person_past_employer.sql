-- Core Person Past Employer Table
-- Stores inferred past employer relationships from salesnav scrape settings
-- Source: when scrape settings have pastCompany.included, all people from that scrape
-- are assumed to have worked at that company previously.

CREATE TABLE IF NOT EXISTS core.person_past_employer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    linkedin_url TEXT NOT NULL,
    past_company_name TEXT,
    past_company_domain TEXT,
    source TEXT,  -- e.g., 'salesnav_scrape_settings'
    scrape_settings_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_person_past_employer_linkedin_url ON core.person_past_employer(linkedin_url);
CREATE INDEX IF NOT EXISTS idx_person_past_employer_company_name ON core.person_past_employer(past_company_name);
CREATE INDEX IF NOT EXISTS idx_person_past_employer_company_domain ON core.person_past_employer(past_company_domain);

-- Unique constraint to prevent duplicates
ALTER TABLE core.person_past_employer
ADD CONSTRAINT person_past_employer_unique
UNIQUE (linkedin_url, past_company_name, past_company_domain);

-- Grant permissions
GRANT SELECT ON core.person_past_employer TO anon, authenticated;
GRANT ALL ON core.person_past_employer TO service_role;
