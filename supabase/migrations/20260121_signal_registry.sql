-- Migration: Signal Registry
-- Description: Registry for tracking all signal types (Clay signals, custom signals, etc.)

CREATE TABLE IF NOT EXISTS reference.signal_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Signal identification
    signal_slug TEXT UNIQUE NOT NULL,
    
    -- Signal classification
    signal_level TEXT NOT NULL CHECK (signal_level IN ('company', 'person')),
    signal_category TEXT NOT NULL,  -- e.g., 'hiring', 'funding', 'job_change', 'promotion', 'news', 'web_intent'
    
    -- Source information
    source TEXT NOT NULL,  -- e.g., 'clay', 'custom', 'crm', 'web_intent'
    source_signal_name TEXT,  -- Original name in source system (e.g., "New Hire" in Clay)
    
    -- Schema information
    required_inputs JSONB,  -- Fields required to trigger/monitor this signal
    output_fields JSONB,    -- Fields the signal produces
    
    -- Metadata
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_signal_registry_level ON reference.signal_registry(signal_level);
CREATE INDEX IF NOT EXISTS idx_signal_registry_category ON reference.signal_registry(signal_category);
CREATE INDEX IF NOT EXISTS idx_signal_registry_source ON reference.signal_registry(source);
CREATE INDEX IF NOT EXISTS idx_signal_registry_active ON reference.signal_registry(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- SEED DATA: Clay Signals
-- =============================================================================

-- Company-level signals
INSERT INTO reference.signal_registry (signal_slug, signal_level, signal_category, source, source_signal_name, required_inputs, output_fields, description)
VALUES 
    ('clay-new-hire', 'company', 'hiring', 'clay', 'New Hire', 
     '{"any_of": ["company_domain", "company_linkedin_url"]}',
     '{"fields": ["company_name", "person_linkedin_url"]}',
     'Detects new hires at monitored companies'),
     
    ('clay-job-posting', 'company', 'hiring', 'clay', 'Job Posting',
     '{"required": ["company_linkedin_url"]}',
     '{"fields": ["company_name", "job_title", "location", "company_domain", "job_linkedin_url", "post_on"]}',
     'Detects new job postings at monitored companies'),
     
    ('clay-news-fundraising', 'company', 'funding', 'clay', 'News & Fundraising',
     '{"required": ["company_domain"]}',
     '{"fields": ["event", "company_record", "company_domains", "news_url", "news_title", "publish_date", "description"]}',
     'Detects news and fundraising events for monitored companies'),
     
    ('clay-web-intent', 'company', 'web_intent', 'clay', 'Web Intent',
     '{"required": []}',
     '{"fields": ["event", "company_domain", "enrich_company", "unique_visited_pages"]}',
     'Detects website visits from companies (presignal/trigger)')
ON CONFLICT (signal_slug) DO NOTHING;

-- Person-level signals
INSERT INTO reference.signal_registry (signal_slug, signal_level, signal_category, source, source_signal_name, required_inputs, output_fields, description)
VALUES 
    ('clay-job-change', 'person', 'job_change', 'clay', 'Job Change',
     '{"required": ["person_linkedin_profile_url"]}',
     '{"fields": ["confidence", "previous_company", "new_company_linkedin_url", "new_company_domain", "new_company_name", "start_date_at_new_job", "started_role_last_3_months", "person_linkedin_profile"]}',
     'Detects when a monitored person changes jobs'),
     
    ('clay-promotion', 'person', 'promotion', 'clay', 'Promotion',
     '{"required": ["person_linkedin_url"]}',
     '{"fields": ["confidence", "previous_title", "new_title", "start_date_with_new_title", "person_linkedin_profile"]}',
     'Detects when a monitored person gets promoted'),
     
    ('clay-linkedin-brand-mention', 'person', 'social', 'clay', 'LinkedIn Post Brand Mentions',
     '{"required": ["person_linkedin_url"]}',
     '{"fields": []}',
     'Detects when a monitored person mentions a brand on LinkedIn')
ON CONFLICT (signal_slug) DO NOTHING;
