-- Migration: ICP Verdicts Table
-- Created: 2026-02-23
-- Purpose: Store Gemini-assessed ICP fit verdicts for job titles against company profiles

CREATE TABLE IF NOT EXISTS core.icp_verdicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    company_domain TEXT NOT NULL,
    company_description TEXT,
    job_title TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reason TEXT,
    assessed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_icp_verdicts_company_domain ON core.icp_verdicts(company_domain);
CREATE INDEX IF NOT EXISTS idx_icp_verdicts_job_title ON core.icp_verdicts(job_title);
CREATE INDEX IF NOT EXISTS idx_icp_verdicts_verdict ON core.icp_verdicts(verdict);

-- Unique constraint for upsert
ALTER TABLE core.icp_verdicts
ADD CONSTRAINT icp_verdicts_unique UNIQUE (company_domain, job_title);

-- Permissions
GRANT SELECT ON core.icp_verdicts TO anon, authenticated;
GRANT ALL ON core.icp_verdicts TO service_role;
