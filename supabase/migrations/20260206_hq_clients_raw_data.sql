-- HQ Clients Raw Data
-- Stores raw uploaded data from HQ clients
-- All fields go into raw_payload JSONB, key fields extracted to columns for querying

CREATE TABLE IF NOT EXISTS hq.clients_raw_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Which HQ client this data belongs to
    client_domain TEXT NOT NULL REFERENCES hq.clients(domain),

    -- Person fields
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    person_linkedin_url TEXT,
    person_city TEXT,
    person_state TEXT,
    person_country TEXT,
    work_email TEXT,
    phone_number TEXT,

    -- Company fields
    company_name TEXT,
    domain TEXT,  -- company domain
    company_linkedin_url TEXT,
    company_city TEXT,
    company_state TEXT,
    company_country TEXT,

    -- Full raw payload (contains everything including title, status, notes, extras)
    raw_payload JSONB NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_client_domain ON hq.clients_raw_data(client_domain);
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_person_linkedin ON hq.clients_raw_data(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_work_email ON hq.clients_raw_data(work_email);
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_company_domain ON hq.clients_raw_data(domain);
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_created ON hq.clients_raw_data(created_at DESC);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_hq_clients_raw_data_payload ON hq.clients_raw_data USING GIN(raw_payload);

-- Grant permissions
GRANT SELECT ON hq.clients_raw_data TO anon, authenticated;
GRANT ALL ON hq.clients_raw_data TO service_role;
