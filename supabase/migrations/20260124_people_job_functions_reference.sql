-- Migration: People Job Functions Reference
-- Description: Reference table for job functions and their sources

CREATE TABLE IF NOT EXISTS reference.people_job_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    source TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (name, source)
);

CREATE INDEX IF NOT EXISTS idx_people_job_functions_name ON reference.people_job_functions(name);
CREATE INDEX IF NOT EXISTS idx_people_job_functions_source ON reference.people_job_functions(source);
