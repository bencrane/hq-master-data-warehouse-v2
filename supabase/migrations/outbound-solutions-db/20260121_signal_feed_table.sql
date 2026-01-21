-- =============================================================================
-- SIGNAL.FEED - Unified signal feed for all clients
-- =============================================================================

CREATE TABLE IF NOT EXISTS signal.feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES core.client(id) ON DELETE CASCADE,
    
    -- Signal metadata
    signal_slug TEXT NOT NULL,  -- 'clay-new-hire', 'clay-promotion', etc.
    signal_level TEXT NOT NULL,  -- 'company' or 'person'
    signal_category TEXT,  -- 'hiring', 'funding', 'job_change', 'promotion', etc.
    
    -- Entity reference (one populated based on level)
    company_domain TEXT,
    company_name TEXT,  -- denormalized for display
    person_linkedin_url TEXT,
    person_name TEXT,  -- denormalized for display
    
    -- Signal payload (denormalized for display, varies by signal type)
    signal_data JSONB NOT NULL,
    
    -- Source reference (to HQ canonical database)
    hq_raw_payload_id UUID,
    hq_extracted_id UUID,
    
    -- Read/action tracking
    is_read BOOLEAN DEFAULT FALSE,
    is_actioned BOOLEAN DEFAULT FALSE,
    actioned_at TIMESTAMPTZ,
    
    -- Timestamps
    signal_detected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Primary query pattern: client's feed, newest first
CREATE INDEX IF NOT EXISTS idx_signal_feed_client_detected 
    ON signal.feed(client_id, signal_detected_at DESC);

-- Filter by signal type
CREATE INDEX IF NOT EXISTS idx_signal_feed_client_slug 
    ON signal.feed(client_id, signal_slug);

-- Filter by entity
CREATE INDEX IF NOT EXISTS idx_signal_feed_company_domain 
    ON signal.feed(company_domain);
CREATE INDEX IF NOT EXISTS idx_signal_feed_person_linkedin 
    ON signal.feed(person_linkedin_url);

-- Filter by read status
CREATE INDEX IF NOT EXISTS idx_signal_feed_client_unread 
    ON signal.feed(client_id, is_read) WHERE is_read = FALSE;

-- Deduplication check (prevent same signal for same client)
CREATE UNIQUE INDEX IF NOT EXISTS idx_signal_feed_dedup 
    ON signal.feed(client_id, signal_slug, hq_extracted_id) 
    WHERE hq_extracted_id IS NOT NULL;
