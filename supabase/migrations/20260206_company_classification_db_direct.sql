-- Company Classification DB Direct Tables
-- For direct OpenAI API calls that write to DB (not via Clay)

-- 1. Add workflow_source to core.company_business_model
ALTER TABLE core.company_business_model
ADD COLUMN IF NOT EXISTS workflow_source TEXT;

-- Update existing records to indicate unknown/legacy source
UPDATE core.company_business_model
SET workflow_source = 'legacy'
WHERE workflow_source IS NULL;

-- 2. Raw table for storing OpenAI request/response
CREATE TABLE IF NOT EXISTS raw.company_classification_db_direct (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,

    -- Input sent to OpenAI
    company_name TEXT,
    description TEXT,

    -- OpenAI request/response
    model TEXT NOT NULL,  -- e.g., 'gpt-4o'
    prompt TEXT,
    response JSONB,
    tokens_used INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_company_classification_db_direct_domain
ON raw.company_classification_db_direct(domain);

-- 3. Extracted table for parsed classification results
CREATE TABLE IF NOT EXISTS extracted.company_classification_db_direct (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_id UUID REFERENCES raw.company_classification_db_direct(id),
    domain TEXT NOT NULL,

    -- Classification results
    is_b2b BOOLEAN,
    b2b_reason TEXT,
    is_b2c BOOLEAN,
    b2c_reason TEXT,

    -- Provenance
    model TEXT,  -- e.g., 'gpt-4o'
    workflow_source TEXT DEFAULT 'openai-native/b2b-b2c/classify/db-direct',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_extracted_company_classification_db_direct_domain
ON extracted.company_classification_db_direct(domain);

CREATE UNIQUE INDEX IF NOT EXISTS idx_extracted_company_classification_db_direct_domain_unique
ON extracted.company_classification_db_direct(domain);

-- Grant permissions
GRANT SELECT ON raw.company_classification_db_direct TO anon, authenticated;
GRANT ALL ON raw.company_classification_db_direct TO service_role;

GRANT SELECT ON extracted.company_classification_db_direct TO anon, authenticated;
GRANT ALL ON extracted.company_classification_db_direct TO service_role;
