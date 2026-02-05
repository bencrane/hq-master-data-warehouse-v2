-- CompanyEnrich Similar Companies Preview — Full Profile Extraction Tables
-- Extracts full company profiles from similar/preview endpoint items

-- 1. Profile (main firmographics)
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_profile (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  name TEXT,
  type TEXT,
  website TEXT,
  industry TEXT,
  industries JSONB,
  description TEXT,
  seo_description TEXT,
  employees TEXT,
  revenue TEXT,
  founded_year INTEGER,
  page_rank NUMERIC,
  categories JSONB,
  naics_codes JSONB,
  keywords JSONB,
  logo_url TEXT,
  companyenrich_id TEXT,
  companyenrich_updated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_profile_domain
  ON extracted.companyenrich_similar_company_profile(domain);

-- 2. Location
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_location (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  city TEXT,
  state TEXT,
  state_code TEXT,
  country TEXT,
  country_code TEXT,
  address TEXT,
  postal_code TEXT,
  phone TEXT,
  latitude NUMERIC,
  longitude NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_location_domain
  ON extracted.companyenrich_similar_company_location(domain);

-- 3. Socials
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_socials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  linkedin_url TEXT,
  linkedin_id TEXT,
  twitter_url TEXT,
  facebook_url TEXT,
  instagram_url TEXT,
  youtube_url TEXT,
  github_url TEXT,
  crunchbase_url TEXT,
  angellist_url TEXT,
  g2_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_socials_domain
  ON extracted.companyenrich_similar_company_socials(domain);

-- 4. Technologies (one row per tech)
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_technologies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  technology TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain, technology)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_tech_domain
  ON extracted.companyenrich_similar_company_technologies(domain);

-- 5. Financial
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_financial (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  funding_stage TEXT,
  total_funding NUMERIC,
  stock_symbol TEXT,
  stock_exchange TEXT,
  latest_funding_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_financial_domain
  ON extracted.companyenrich_similar_company_financial(domain);

-- 6. Funding Rounds (one row per round)
CREATE TABLE IF NOT EXISTS extracted.companyenrich_similar_company_funding_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain TEXT NOT NULL,
  funding_type TEXT,
  amount NUMERIC,
  funding_date TIMESTAMPTZ,
  investors TEXT,
  url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (domain, funding_type, funding_date)
);

CREATE INDEX IF NOT EXISTS idx_ce_similar_funding_rounds_domain
  ON extracted.companyenrich_similar_company_funding_rounds(domain);

-- Permissions
GRANT SELECT ON extracted.companyenrich_similar_company_profile TO anon, authenticated;
GRANT SELECT ON extracted.companyenrich_similar_company_location TO anon, authenticated;
GRANT SELECT ON extracted.companyenrich_similar_company_socials TO anon, authenticated;
GRANT SELECT ON extracted.companyenrich_similar_company_technologies TO anon, authenticated;
GRANT SELECT ON extracted.companyenrich_similar_company_financial TO anon, authenticated;
GRANT SELECT ON extracted.companyenrich_similar_company_funding_rounds TO anon, authenticated;

GRANT ALL ON extracted.companyenrich_similar_company_profile TO service_role;
GRANT ALL ON extracted.companyenrich_similar_company_location TO service_role;
GRANT ALL ON extracted.companyenrich_similar_company_socials TO service_role;
GRANT ALL ON extracted.companyenrich_similar_company_technologies TO service_role;
GRANT ALL ON extracted.companyenrich_similar_company_financial TO service_role;
GRANT ALL ON extracted.companyenrich_similar_company_funding_rounds TO service_role;
