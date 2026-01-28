-- Company Star Schema Migration
-- Creates dimension tables for company data with source attribution
-- and missing reference tables for normalization

-- ============================================================================
-- REFERENCE TABLES (Canonical Values)
-- ============================================================================

-- Company Types (Public Company, Private Company, etc.)
CREATE TABLE IF NOT EXISTS reference.company_types (
    name TEXT PRIMARY KEY,
    sort_order INTEGER DEFAULT 0
);

INSERT INTO reference.company_types (name, sort_order) VALUES
    ('Public Company', 1),
    ('Private Company', 2),
    ('Nonprofit', 3),
    ('Educational Institution', 4),
    ('Government Agency', 5),
    ('Self-Employed', 6),
    ('Partnership', 7)
ON CONFLICT (name) DO NOTHING;

-- Funding Ranges (standardized funding buckets)
CREATE TABLE IF NOT EXISTS reference.funding_ranges (
    name TEXT PRIMARY KEY,
    min_funding_usd BIGINT,
    max_funding_usd BIGINT,
    sort_order INTEGER DEFAULT 0
);

INSERT INTO reference.funding_ranges (name, min_funding_usd, max_funding_usd, sort_order) VALUES
    ('Bootstrapped', 0, 0, 1),
    ('< $1M', 1, 999999, 2),
    ('$1M - $5M', 1000000, 4999999, 3),
    ('$5M - $10M', 5000000, 9999999, 4),
    ('$10M - $25M', 10000000, 24999999, 5),
    ('$25M - $50M', 25000000, 49999999, 6),
    ('$50M - $100M', 50000000, 99999999, 7),
    ('$100M - $250M', 100000000, 249999999, 8),
    ('$250M - $500M', 250000000, 499999999, 9),
    ('$500M - $1B', 500000000, 999999999, 10),
    ('$1B+', 1000000000, NULL, 11)
ON CONFLICT (name) DO NOTHING;

-- Revenue Ranges (standardized revenue buckets)
CREATE TABLE IF NOT EXISTS reference.revenue_ranges (
    name TEXT PRIMARY KEY,
    min_revenue_usd BIGINT,
    max_revenue_usd BIGINT,
    sort_order INTEGER DEFAULT 0
);

INSERT INTO reference.revenue_ranges (name, min_revenue_usd, max_revenue_usd, sort_order) VALUES
    ('< $1M', 0, 999999, 1),
    ('$1M - $5M', 1000000, 4999999, 2),
    ('$5M - $10M', 5000000, 9999999, 3),
    ('$10M - $25M', 10000000, 24999999, 4),
    ('$25M - $50M', 25000000, 49999999, 5),
    ('$50M - $100M', 50000000, 99999999, 6),
    ('$100M - $500M', 100000000, 499999999, 7),
    ('$500M - $1B', 500000000, 999999999, 8),
    ('$1B - $10B', 1000000000, 9999999999, 9),
    ('$10B - $100B', 10000000000, 99999999999, 10),
    ('$100B+', 100000000000, NULL, 11)
ON CONFLICT (name) DO NOTHING;

-- Lookup table for Clay funding range strings
CREATE TABLE IF NOT EXISTS reference.funding_range_lookup (
    raw_value TEXT PRIMARY KEY,
    matched_funding_range TEXT REFERENCES reference.funding_ranges(name)
);

INSERT INTO reference.funding_range_lookup (raw_value, matched_funding_range) VALUES
    ('$0 - $1M', '< $1M'),
    ('$1M - $5M', '$1M - $5M'),
    ('$5M - $10M', '$5M - $10M'),
    ('$10M - $25M', '$10M - $25M'),
    ('$25M - $50M', '$25M - $50M'),
    ('$50M - $100M', '$50M - $100M'),
    ('$100M - $250M', '$100M - $250M'),
    ('$250M - $500M', '$250M - $500M'),
    ('$500M - $1B', '$500M - $1B'),
    ('$1B+', '$1B+')
ON CONFLICT (raw_value) DO NOTHING;

-- Lookup table for Clay revenue range strings
CREATE TABLE IF NOT EXISTS reference.revenue_range_lookup (
    raw_value TEXT PRIMARY KEY,
    matched_revenue_range TEXT REFERENCES reference.revenue_ranges(name)
);

INSERT INTO reference.revenue_range_lookup (raw_value, matched_revenue_range) VALUES
    ('$0-$1M', '< $1M'),
    ('$1M-$5M', '$1M - $5M'),
    ('$5M-$10M', '$5M - $10M'),
    ('$10M-$25M', '$10M - $25M'),
    ('$25M-$50M', '$25M - $50M'),
    ('$50M-$100M', '$50M - $100M'),
    ('$100M-$500M', '$100M - $500M'),
    ('$500M-$1B', '$500M - $1B'),
    ('$1B-$10B', '$1B - $10B'),
    ('$10B-$100B', '$10B - $100B'),
    ('100B-1T', '$100B+'),
    ('$100B-$1T', '$100B+')
ON CONFLICT (raw_value) DO NOTHING;

-- ============================================================================
-- DIMENSION TABLES (Star Schema)
-- Each table: domain + source as composite key, raw values, matched/derived values
-- ============================================================================

-- Company Names Dimension
-- Tracks raw names from each source and normalized versions
CREATE TABLE IF NOT EXISTS core.company_names (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'clay', 'crunchbase', 'apollo', 'linkedin', etc.

    -- Raw values from source
    raw_name TEXT,

    -- Derived/normalized values
    cleaned_name TEXT,  -- Our cleaned/normalized version
    linkedin_url TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_names_domain ON core.company_names(domain);

-- Company Employee Ranges Dimension
CREATE TABLE IF NOT EXISTS core.company_employee_ranges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_size TEXT,  -- e.g., "10,001+ employees", "51-200"
    raw_employee_count INTEGER,  -- If source provides exact count

    -- Matched values (from reference.employee_ranges)
    matched_employee_range TEXT REFERENCES reference.employee_ranges(name),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_employee_ranges_domain ON core.company_employee_ranges(domain);

-- Company Types Dimension
CREATE TABLE IF NOT EXISTS core.company_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_type TEXT,  -- e.g., "Public Company", "Privately Held"

    -- Matched values (from reference.company_types)
    matched_type TEXT REFERENCES reference.company_types(name),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_types_domain ON core.company_types(domain);

-- Company Locations Dimension
-- Has both raw location string AND parsed/derived city/state/country
CREATE TABLE IF NOT EXISTS core.company_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_location TEXT,  -- e.g., "Mountain View, CA"
    raw_country TEXT,   -- e.g., "United States"

    -- Derived/parsed values (from location lookup tables)
    matched_city TEXT,
    matched_state TEXT,
    matched_country TEXT,
    has_city BOOLEAN DEFAULT FALSE,
    has_state BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_locations_domain ON core.company_locations(domain);
CREATE INDEX IF NOT EXISTS idx_company_locations_country ON core.company_locations(matched_country);

-- Company Industries Dimension
CREATE TABLE IF NOT EXISTS core.company_industries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_industry TEXT,      -- Primary industry string
    raw_industries JSONB,   -- Array of industries if provided

    -- Matched values (from reference.company_industries)
    matched_industry TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_industries_domain ON core.company_industries(domain);
CREATE INDEX IF NOT EXISTS idx_company_industries_matched ON core.company_industries(matched_industry);

-- Company Funding Dimension
CREATE TABLE IF NOT EXISTS core.company_funding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_funding_range TEXT,  -- e.g., "$100M - $250M"
    raw_funding_amount BIGINT,  -- If exact amount provided

    -- Matched values (from reference.funding_ranges)
    matched_funding_range TEXT REFERENCES reference.funding_ranges(name),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_funding_domain ON core.company_funding(domain);

-- Company Revenue Dimension
CREATE TABLE IF NOT EXISTS core.company_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    -- Raw values from source
    raw_revenue_range TEXT,  -- e.g., "100B-1T"
    raw_revenue_amount BIGINT,  -- If exact amount provided

    -- Matched values (from reference.revenue_ranges)
    matched_revenue_range TEXT REFERENCES reference.revenue_ranges(name),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_revenue_domain ON core.company_revenue(domain);

-- Company Descriptions Dimension (if not already exists)
-- Tracks descriptions from each source
CREATE TABLE IF NOT EXISTS core.company_descriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    source TEXT NOT NULL,

    description TEXT,
    tagline TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(domain, source)
);

CREATE INDEX IF NOT EXISTS idx_company_descriptions_domain ON core.company_descriptions(domain);

-- ============================================================================
-- COALESCED VIEW (Single source of truth for frontend)
-- Joins all dimension tables and coalesces values with priority order
-- ============================================================================

CREATE OR REPLACE VIEW core.companies_full_v2 AS
SELECT
    -- Domain is the primary key
    COALESCE(n.domain, er.domain, t.domain, l.domain, i.domain, f.domain, r.domain, d.domain) AS domain,

    -- Names (prefer crunchbase > clay > apollo)
    COALESCE(
        (SELECT cleaned_name FROM core.company_names WHERE domain = n.domain AND source = 'crunchbase'),
        (SELECT cleaned_name FROM core.company_names WHERE domain = n.domain AND source = 'clay'),
        (SELECT raw_name FROM core.company_names WHERE domain = n.domain AND source = 'crunchbase'),
        (SELECT raw_name FROM core.company_names WHERE domain = n.domain AND source = 'clay'),
        n.raw_name
    ) AS name,

    -- LinkedIn URL (any source)
    (SELECT linkedin_url FROM core.company_names WHERE domain = n.domain AND linkedin_url IS NOT NULL LIMIT 1) AS linkedin_url,

    -- Employee Range (coalesced)
    COALESCE(
        er.matched_employee_range,
        (SELECT matched_employee_range FROM core.company_employee_ranges WHERE domain = er.domain AND matched_employee_range IS NOT NULL LIMIT 1)
    ) AS employee_range,

    -- Company Type
    COALESCE(
        t.matched_type,
        (SELECT matched_type FROM core.company_types WHERE domain = t.domain AND matched_type IS NOT NULL LIMIT 1)
    ) AS company_type,

    -- Location (coalesced)
    COALESCE(l.matched_city, (SELECT matched_city FROM core.company_locations WHERE domain = l.domain AND matched_city IS NOT NULL LIMIT 1)) AS company_city,
    COALESCE(l.matched_state, (SELECT matched_state FROM core.company_locations WHERE domain = l.domain AND matched_state IS NOT NULL LIMIT 1)) AS company_state,
    COALESCE(l.matched_country, (SELECT matched_country FROM core.company_locations WHERE domain = l.domain AND matched_country IS NOT NULL LIMIT 1)) AS company_country,

    -- Industry (coalesced)
    COALESCE(
        i.matched_industry,
        (SELECT matched_industry FROM core.company_industries WHERE domain = i.domain AND matched_industry IS NOT NULL LIMIT 1)
    ) AS matched_industry,

    -- Funding
    COALESCE(
        f.matched_funding_range,
        (SELECT matched_funding_range FROM core.company_funding WHERE domain = f.domain AND matched_funding_range IS NOT NULL LIMIT 1)
    ) AS funding_range,

    -- Revenue
    COALESCE(
        r.matched_revenue_range,
        (SELECT matched_revenue_range FROM core.company_revenue WHERE domain = r.domain AND matched_revenue_range IS NOT NULL LIMIT 1)
    ) AS revenue_range,

    -- Description (prefer longest)
    (SELECT description FROM core.company_descriptions WHERE domain = d.domain ORDER BY LENGTH(description) DESC NULLS LAST LIMIT 1) AS description,
    (SELECT tagline FROM core.company_descriptions WHERE domain = d.domain AND tagline IS NOT NULL LIMIT 1) AS tagline

FROM core.company_names n
FULL OUTER JOIN core.company_employee_ranges er ON n.domain = er.domain
FULL OUTER JOIN core.company_types t ON COALESCE(n.domain, er.domain) = t.domain
FULL OUTER JOIN core.company_locations l ON COALESCE(n.domain, er.domain, t.domain) = l.domain
FULL OUTER JOIN core.company_industries i ON COALESCE(n.domain, er.domain, t.domain, l.domain) = i.domain
FULL OUTER JOIN core.company_funding f ON COALESCE(n.domain, er.domain, t.domain, l.domain, i.domain) = f.domain
FULL OUTER JOIN core.company_revenue r ON COALESCE(n.domain, er.domain, t.domain, l.domain, i.domain, f.domain) = r.domain
FULL OUTER JOIN core.company_descriptions d ON COALESCE(n.domain, er.domain, t.domain, l.domain, i.domain, f.domain, r.domain) = d.domain
GROUP BY
    COALESCE(n.domain, er.domain, t.domain, l.domain, i.domain, f.domain, r.domain, d.domain),
    n.domain, n.raw_name,
    er.domain, er.matched_employee_range,
    t.domain, t.matched_type,
    l.domain, l.matched_city, l.matched_state, l.matched_country,
    i.domain, i.matched_industry,
    f.domain, f.matched_funding_range,
    r.domain, r.matched_revenue_range,
    d.domain;

-- Grant permissions
GRANT SELECT ON core.companies_full_v2 TO authenticated;
GRANT SELECT ON core.companies_full_v2 TO anon;
