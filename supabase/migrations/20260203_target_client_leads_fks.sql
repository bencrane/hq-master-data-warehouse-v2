-- Add FK columns to target_client.leads for linking to core tables
-- This enables direct joins to enriched company/person data

ALTER TABLE target_client.leads
ADD COLUMN IF NOT EXISTS core_company_id UUID REFERENCES core.companies(id),
ADD COLUMN IF NOT EXISTS core_person_id UUID REFERENCES core.people(id);

-- Indexes for join performance
CREATE INDEX IF NOT EXISTS idx_target_client_leads_core_company
ON target_client.leads(core_company_id);

CREATE INDEX IF NOT EXISTS idx_target_client_leads_core_person
ON target_client.leads(core_person_id);
