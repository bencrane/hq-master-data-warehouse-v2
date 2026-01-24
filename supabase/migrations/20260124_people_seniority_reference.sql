-- Migration: People Seniority Reference
-- Description: Reference table for seniority levels and their sources

CREATE TABLE IF NOT EXISTS reference.people_seniority (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    source TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (name, source)
);

CREATE INDEX IF NOT EXISTS idx_people_seniority_name ON reference.people_seniority(name);
CREATE INDEX IF NOT EXISTS idx_people_seniority_source ON reference.people_seniority(source);
