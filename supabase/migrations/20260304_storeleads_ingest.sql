-- Storeleads Ingestion Tables
-- Raw payload storage and extracted company/technology data

-- ============================================================================
-- RAW TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS raw.storeleads_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    merchant_name TEXT,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_storeleads_payloads_domain ON raw.storeleads_payloads(domain);
CREATE INDEX IF NOT EXISTS idx_storeleads_payloads_created_at ON raw.storeleads_payloads(created_at);

COMMENT ON TABLE raw.storeleads_payloads IS 'Raw Storeleads payloads from Clay enrichment';

-- ============================================================================
-- EXTRACTED TABLES
-- ============================================================================

-- Main company firmographic data
CREATE TABLE IF NOT EXISTS extracted.storeleads_company (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.storeleads_payloads(id),
    domain TEXT NOT NULL,
    merchant_name TEXT,

    -- Location
    city TEXT,
    location TEXT,
    country_code TEXT,
    region TEXT,
    subregion TEXT,
    administrative_area_level_1 TEXT,
    latitude NUMERIC,
    longitude NUMERIC,

    -- Company info
    title TEXT,
    description TEXT,
    platform TEXT,
    employee_count INTEGER,
    product_count INTEGER,

    -- Revenue / Traffic estimates
    estimated_sales NUMERIC,
    estimated_sales_yearly NUMERIC,
    estimated_visits INTEGER,
    estimated_page_views INTEGER,

    -- Rankings
    rank INTEGER,
    cc_rank INTEGER,
    cc_centrality INTEGER,
    platform_rank INTEGER,
    rank_percentile NUMERIC,
    platform_rank_percentile NUMERIC,

    -- Trustpilot
    trustpilot_avg_rating NUMERIC,
    trustpilot_review_count INTEGER,

    -- Arrays stored as JSONB
    categories JSONB,
    features JSONB,
    shipping_carriers JSONB,
    cluster_domains JSONB,
    aliases JSONB,
    redirects_to JSONB,
    contact_info JSONB,

    -- URLs
    linkedin_url TEXT,
    about_us TEXT,
    career_page TEXT,
    contact_page TEXT,
    brands_page TEXT,
    tracking_page TEXT,
    store_locator_page TEXT,
    og_image TEXT,
    icon TEXT,

    -- Metadata
    language_code TEXT,
    state TEXT,
    last_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_storeleads_company_domain ON extracted.storeleads_company(domain);
CREATE INDEX IF NOT EXISTS idx_storeleads_company_raw_payload_id ON extracted.storeleads_company(raw_payload_id);
CREATE INDEX IF NOT EXISTS idx_storeleads_company_country_code ON extracted.storeleads_company(country_code);
CREATE INDEX IF NOT EXISTS idx_storeleads_company_platform ON extracted.storeleads_company(platform);

COMMENT ON TABLE extracted.storeleads_company IS 'Extracted Storeleads company firmographic data';

-- Technology stack (one row per technology per domain)
CREATE TABLE IF NOT EXISTS extracted.storeleads_technology (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.storeleads_payloads(id),
    storeleads_company_id UUID REFERENCES extracted.storeleads_company(id),
    domain TEXT NOT NULL,

    -- Technology info
    name TEXT NOT NULL,
    icon_url TEXT,
    vendor_url TEXT,
    description TEXT,
    installs INTEGER,
    categories JSONB,
    installed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_storeleads_technology_domain ON extracted.storeleads_technology(domain);
CREATE INDEX IF NOT EXISTS idx_storeleads_technology_name ON extracted.storeleads_technology(name);
CREATE INDEX IF NOT EXISTS idx_storeleads_technology_raw_payload_id ON extracted.storeleads_technology(raw_payload_id);
CREATE INDEX IF NOT EXISTS idx_storeleads_technology_company_id ON extracted.storeleads_technology(storeleads_company_id);

COMMENT ON TABLE extracted.storeleads_technology IS 'Extracted Storeleads technology stack per company';

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT ON raw.storeleads_payloads TO authenticated;
GRANT SELECT ON extracted.storeleads_company TO authenticated;
GRANT SELECT ON extracted.storeleads_technology TO authenticated;

-- ============================================================================
-- WORKFLOW REGISTRY
-- ============================================================================

INSERT INTO reference.enrichment_workflow_registry
(workflow_slug, provider, platform, payload_type, entity_type, description)
VALUES (
  'storeleads-company-enrichment',
  'storeleads',
  'clay',
  'enrichment',
  'company',
  'Storeleads company firmographic and technology stack data'
)
ON CONFLICT (workflow_slug) DO NOTHING;
