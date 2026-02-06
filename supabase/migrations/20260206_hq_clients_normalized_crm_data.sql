-- HQ Clients Normalized
-- Stores normalized data from hq.clients_raw_data
-- Written to by the normalization workflow (not on ingest)

CREATE TABLE IF NOT EXISTS hq.clients_normalized_crm_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link back to raw data
    raw_data_id UUID REFERENCES hq.clients_raw_data(id),

    -- Which HQ client this data belongs to
    client_domain TEXT NOT NULL REFERENCES hq.clients(domain),

    -- Person fields (normalized)
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    person_linkedin_url TEXT,
    person_city TEXT,
    person_state TEXT,
    person_country TEXT,
    work_email TEXT,
    phone_number TEXT,

    -- Company fields (company_name NOT normalized, kept as-is)
    company_name TEXT,
    domain TEXT,  -- normalized company domain
    company_linkedin_url TEXT,
    company_city TEXT,
    company_state TEXT,
    company_country TEXT,

    -- Workflow tracking
    normalized_at TIMESTAMPTZ DEFAULT NOW(),
    workflow_version TEXT DEFAULT '1.0',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_client_domain ON hq.clients_normalized_crm_data(client_domain);
CREATE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_raw_data_id ON hq.clients_normalized_crm_data(raw_data_id);
CREATE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_domain ON hq.clients_normalized_crm_data(domain);
CREATE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_work_email ON hq.clients_normalized_crm_data(work_email);
CREATE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_person_linkedin ON hq.clients_normalized_crm_data(person_linkedin_url);

-- Additional fields from raw_payload
ALTER TABLE hq.clients_normalized_crm_data ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE hq.clients_normalized_crm_data ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE hq.clients_normalized_crm_data ADD COLUMN IF NOT EXISTS notes TEXT;

-- Unique constraint on raw_data_id for upsert
CREATE UNIQUE INDEX IF NOT EXISTS idx_hq_clients_normalized_crm_data_raw_data_id_unique
ON hq.clients_normalized_crm_data(raw_data_id);

-- Grant permissions
GRANT SELECT ON hq.clients_normalized_crm_data TO anon, authenticated;
GRANT ALL ON hq.clients_normalized_crm_data TO service_role;
