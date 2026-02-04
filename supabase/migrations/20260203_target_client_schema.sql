-- Target Client Schema
-- For demo/prospect leads (separate from paying client leads)
--
-- Usage: target_client_domain identifies the prospect being demoed to
-- Data in core.* remains independent - this is just a pointer table

CREATE SCHEMA IF NOT EXISTS target_client;

-- target_client.leads (mirrors client.leads)
CREATE TABLE target_client.leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_client_domain TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    person_linkedin_url TEXT,
    work_email TEXT,
    company_domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,
    source TEXT,
    form_id TEXT,
    form_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_target_client_leads_domain ON target_client.leads(target_client_domain);

-- target_client.leads_people (normalized person data)
CREATE TABLE target_client.leads_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_client_domain TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    person_linkedin_url TEXT,
    work_email TEXT,
    company_domain TEXT,
    source TEXT,
    form_id TEXT,
    form_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_target_client_leads_people_domain ON target_client.leads_people(target_client_domain);

-- target_client.leads_companies (normalized company data)
CREATE TABLE target_client.leads_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_client_domain TEXT NOT NULL,
    company_domain TEXT,
    company_name TEXT,
    company_linkedin_url TEXT,
    source TEXT,
    form_id TEXT,
    form_title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_target_client_leads_companies_domain ON target_client.leads_companies(target_client_domain);
