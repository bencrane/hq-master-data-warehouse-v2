-- HQ Schema
-- Internal HQ tables for tracking clients and services

CREATE SCHEMA IF NOT EXISTS hq;

-- hq.clients - HQ's paying clients
CREATE TABLE IF NOT EXISTS hq.clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    domain TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'active',
    service TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add service column if missing (for existing tables)
ALTER TABLE hq.clients ADD COLUMN IF NOT EXISTS service TEXT;

CREATE INDEX IF NOT EXISTS idx_hq_clients_domain ON hq.clients(domain);
CREATE INDEX IF NOT EXISTS idx_hq_clients_service ON hq.clients(service);

-- Grant permissions
GRANT USAGE ON SCHEMA hq TO anon, authenticated, service_role;
GRANT SELECT ON hq.clients TO anon, authenticated;
GRANT ALL ON hq.clients TO service_role;

-- Insert SecurityPal AI (or update if exists)
INSERT INTO hq.clients (name, domain, service)
VALUES ('SecurityPal AI', 'securitypalhq.com', 'crm-data-enrichment')
ON CONFLICT (domain) DO UPDATE SET service = EXCLUDED.service;
