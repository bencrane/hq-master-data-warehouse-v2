-- ICP Criteria - Unified table for all ICP filter criteria
-- Single source for company and people filters

CREATE TABLE IF NOT EXISTS core.icp_criteria (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Key
    domain TEXT NOT NULL UNIQUE,
    company_name TEXT,

    -- Company filters
    industries JSONB,              -- ["Computer & Network Security", "Software Development"]
    countries JSONB,               -- ["United States", "Canada"]
    employee_ranges JSONB,         -- ["51-200", "201-500"]
    funding_stages JSONB,          -- ["Series A", "Series B", "Series C"]

    -- People filters
    job_titles JSONB,              -- ["Chief Information Security Officer", "VP of Security"]
    seniorities JSONB,             -- ["VP", "Director", "C-Suite"]
    job_functions JSONB,           -- ["Security", "IT", "Compliance"]

    -- Value prop (for display)
    value_proposition TEXT,
    core_benefit TEXT,
    target_customer TEXT,
    key_differentiator TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_icp_criteria_domain ON core.icp_criteria(domain);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON core.icp_criteria TO authenticated;
GRANT SELECT ON core.icp_criteria TO anon;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION core.update_icp_criteria_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_icp_criteria_updated_at ON core.icp_criteria;
CREATE TRIGGER trigger_icp_criteria_updated_at
    BEFORE UPDATE ON core.icp_criteria
    FOR EACH ROW
    EXECUTE FUNCTION core.update_icp_criteria_updated_at();
