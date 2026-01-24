-- Migration: Company Industries Reference
-- Description: Reference table for industry names and their sources

CREATE TABLE IF NOT EXISTS reference.company_industries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    source TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (name, source)
);

CREATE INDEX IF NOT EXISTS idx_company_industries_name ON reference.company_industries(name);
CREATE INDEX IF NOT EXISTS idx_company_industries_source ON reference.company_industries(source);
