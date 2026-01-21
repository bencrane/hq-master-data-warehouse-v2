-- =============================================================================
-- SIGNAL.REGISTRY - Signal type definitions (mirrors HQ reference.signal_registry)
-- =============================================================================

CREATE TABLE IF NOT EXISTS signal.registry (
    signal_slug TEXT PRIMARY KEY,
    signal_level TEXT NOT NULL,  -- 'company' or 'person'
    signal_category TEXT NOT NULL,  -- 'hiring', 'funding', 'job_change', 'promotion', 'news', 'web_intent', 'social'
    source TEXT NOT NULL,  -- 'clay', 'custom', 'crm'
    display_name TEXT NOT NULL,  -- Human-readable name for UI
    description TEXT,
    icon TEXT,  -- Icon identifier for UI
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with Clay signals
INSERT INTO signal.registry (signal_slug, signal_level, signal_category, source, display_name, description) VALUES
('clay-new-hire', 'company', 'hiring', 'clay', 'New Hire', 'A new person was hired at this company.'),
('clay-job-posting', 'company', 'hiring', 'clay', 'Job Posting', 'This company posted a new job opening.'),
('clay-news-fundraising', 'company', 'funding', 'clay', 'News & Fundraising', 'News or fundraising event detected for this company.'),
('clay-web-intent', 'company', 'web_intent', 'clay', 'Web Intent', 'This company visited your website.'),
('clay-job-change', 'person', 'job_change', 'clay', 'Job Change', 'This person changed jobs.'),
('clay-promotion', 'person', 'promotion', 'clay', 'Promotion', 'This person received a promotion.'),
('clay-linkedin-brand-mention', 'person', 'social', 'clay', 'Brand Mention', 'This person mentioned a brand on LinkedIn.')
ON CONFLICT (signal_slug) DO NOTHING;
