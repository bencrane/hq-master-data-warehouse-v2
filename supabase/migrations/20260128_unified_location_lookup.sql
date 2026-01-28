-- Migration: Unified Location Lookup
-- Description: Consolidates all location parsing lookup tables into one
-- NOTE: Original tables are NOT deleted - this is additive only

-- =============================================================================
-- CREATE UNIFIED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS reference.location_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The raw location string (exact match lookup)
    raw_location TEXT NOT NULL,

    -- Source table this came from
    source TEXT NOT NULL,

    -- Parsed components
    city TEXT,
    state TEXT,
    country TEXT,

    -- Flags
    has_city BOOLEAN DEFAULT false,
    has_state BOOLEAN DEFAULT false,
    has_country BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for exact match lookups
CREATE INDEX IF NOT EXISTS idx_location_parsed_raw_location
    ON reference.location_parsed(raw_location);

-- Index for source filtering
CREATE INDEX IF NOT EXISTS idx_location_parsed_source
    ON reference.location_parsed(source);

-- Composite index for exact match by source
CREATE INDEX IF NOT EXISTS idx_location_parsed_raw_source
    ON reference.location_parsed(raw_location, source);

-- =============================================================================
-- INSERT FROM ALL 7 SOURCE TABLES
-- =============================================================================

-- 1. location_lookup (9,667 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    location_name,
    'location-lookup',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    COALESCE(has_country, false)
FROM reference.location_lookup;

-- 2. company_location_lookup (21,706 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    location,
    'company-location-lookup',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    false  -- has_country not in original table
FROM reference.company_location_lookup;

-- 3. clay_enriched_company_location_lookup (5,963 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    locality,
    'clay-enriched-company',
    city,
    state,
    COALESCE(country_full, country),  -- prefer full name if available
    city IS NOT NULL,
    state IS NOT NULL,
    country IS NOT NULL OR country_full IS NOT NULL
FROM reference.clay_enriched_company_location_lookup;

-- 4. clay_find_companies_location_lookup (3,682 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    location_name,
    'clay-find-companies',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    COALESCE(has_country, false)
FROM reference.clay_find_companies_location_lookup;

-- 5. clay_find_people_location_lookup (3,943 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    location_name,
    'clay-find-people',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    COALESCE(has_country, false)
FROM reference.clay_find_people_location_lookup;

-- 6. salesnav_company_location_lookup (3,602 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    registered_address_raw,
    'salesnav-company',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    COALESCE(has_country, false)
FROM reference.salesnav_company_location_lookup;

-- 7. salesnav_location_lookup (4,321 rows)
INSERT INTO reference.location_parsed (raw_location, source, city, state, country, has_city, has_state, has_country)
SELECT
    location_raw,
    'salesnav-location',
    city,
    state,
    country,
    COALESCE(has_city, false),
    COALESCE(has_state, false),
    COALESCE(has_country, false)
FROM reference.salesnav_location_lookup;
