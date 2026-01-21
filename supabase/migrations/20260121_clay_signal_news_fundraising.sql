-- Migration: Clay Signal - News & Fundraising
-- Description: Tables for storing Clay "News & Fundraising" signal payloads and extracted data
-- Signal Type: Company-level
-- Required Input: company_domain
-- Flattened Output: news_url, news_title, publish_date, description

-- =============================================================================
-- RAW TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.clay_news_fundraising_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Input fields
    company_domain TEXT NOT NULL,
    
    -- Signal metadata (references reference.signal_registry)
    signal_slug TEXT NOT NULL,
    
    -- Traceability
    clay_table_url TEXT,
    
    -- Full Clay event payload (stored as-is)
    raw_event_payload JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for raw table
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_payloads_company_domain 
    ON raw.clay_news_fundraising_payloads(company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_payloads_created_at 
    ON raw.clay_news_fundraising_payloads(created_at DESC);

-- =============================================================================
-- EXTRACTED TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted.clay_news_fundraising (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.clay_news_fundraising_payloads(id),
    
    -- Input context (denormalized for query convenience)
    company_domain TEXT NOT NULL,
    
    -- Extracted fields (flattened from Clay output)
    news_url TEXT,
    news_title TEXT,
    publish_date DATE,
    description TEXT,
    
    -- Signal metadata
    signal_detected_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for extracted table
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_company_domain 
    ON extracted.clay_news_fundraising(company_domain);
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_news_url 
    ON extracted.clay_news_fundraising(news_url);
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_publish_date 
    ON extracted.clay_news_fundraising(publish_date DESC);
CREATE INDEX IF NOT EXISTS idx_clay_news_fundraising_signal_detected_at 
    ON extracted.clay_news_fundraising(signal_detected_at DESC);

-- =============================================================================
-- NOTE: Signal registry entry is in 20260121_signal_registry.sql
-- Signal slug: clay-news-fundraising
-- =============================================================================
