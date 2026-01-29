-- Company Enrich Similar Companies Tables
-- Migration for storing similar companies from companyenrich.com API

-- Batch tracking table (logs when companies go through)
CREATE TABLE IF NOT EXISTS raw.company_enrich_similar_batches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_name TEXT,
  input_domains TEXT[],
  similarity_weight NUMERIC,
  country_code TEXT,
  status TEXT DEFAULT 'pending',
  total_domains INTEGER,
  processed_domains INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_company_enrich_batches_status ON raw.company_enrich_similar_batches(status);

-- Raw payload table (per domain)
CREATE TABLE IF NOT EXISTS raw.company_enrich_similar_raw (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID REFERENCES raw.company_enrich_similar_batches(id),
  input_domain TEXT NOT NULL,
  similarity_weight NUMERIC,
  country_code TEXT,
  raw_response JSONB,
  status_code INTEGER,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_enrich_similar_raw_domain ON raw.company_enrich_similar_raw(input_domain);
CREATE INDEX IF NOT EXISTS idx_company_enrich_similar_raw_batch ON raw.company_enrich_similar_raw(batch_id);

-- Extracted similar companies
CREATE TABLE IF NOT EXISTS extracted.company_enrich_similar (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_id UUID REFERENCES raw.company_enrich_similar_raw(id),
  batch_id UUID REFERENCES raw.company_enrich_similar_batches(id),
  input_domain TEXT NOT NULL,
  company_id UUID,
  company_name TEXT,
  company_domain TEXT,
  company_website TEXT,
  company_industry TEXT,
  company_description TEXT,
  company_keywords TEXT[],
  company_logo_url TEXT,
  similarity_score NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_enrich_similar_input ON extracted.company_enrich_similar(input_domain);
CREATE INDEX IF NOT EXISTS idx_company_enrich_similar_domain ON extracted.company_enrich_similar(company_domain);
CREATE INDEX IF NOT EXISTS idx_company_enrich_similar_batch ON extracted.company_enrich_similar(batch_id);

-- Permissions
GRANT SELECT ON raw.company_enrich_similar_batches TO anon, authenticated;
GRANT SELECT ON raw.company_enrich_similar_raw TO anon, authenticated;
GRANT SELECT ON extracted.company_enrich_similar TO anon, authenticated;
GRANT ALL ON raw.company_enrich_similar_batches TO service_role;
GRANT ALL ON raw.company_enrich_similar_raw TO service_role;
GRANT ALL ON extracted.company_enrich_similar TO service_role;
