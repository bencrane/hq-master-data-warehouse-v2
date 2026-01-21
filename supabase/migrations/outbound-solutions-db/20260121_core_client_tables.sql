-- =============================================================================
-- CORE.CLIENT - Your customers using the outbound platform
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.client (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,  -- e.g., "acme-corp"
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_slug ON core.client(slug);
CREATE INDEX IF NOT EXISTS idx_client_is_active ON core.client(is_active);

-- =============================================================================
-- CORE.CLIENT_COMPANY - Companies in a client's TAM
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.client_company (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES core.client(id) ON DELETE CASCADE,
    
    -- Company identifiers (links to HQ data)
    company_domain TEXT NOT NULL,
    company_linkedin_url TEXT,
    company_name TEXT,  -- denormalized for display
    
    -- Tracking metadata
    added_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT,  -- 'manual', 'import', 'web_intent', 'crm_sync'
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(client_id, company_domain)
);

CREATE INDEX IF NOT EXISTS idx_client_company_client_id ON core.client_company(client_id);
CREATE INDEX IF NOT EXISTS idx_client_company_domain ON core.client_company(company_domain);
CREATE INDEX IF NOT EXISTS idx_client_company_source ON core.client_company(source);

-- =============================================================================
-- CORE.CLIENT_PERSON - People a client is tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.client_person (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES core.client(id) ON DELETE CASCADE,
    
    -- Person identifiers (links to HQ data)
    person_linkedin_url TEXT NOT NULL,
    person_name TEXT,  -- denormalized for display
    person_title TEXT,  -- denormalized for display
    company_domain TEXT,  -- current company, for context
    
    -- Tracking metadata
    added_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT,  -- 'manual', 'import', 'crm_sync', 'enrichment'
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(client_id, person_linkedin_url)
);

CREATE INDEX IF NOT EXISTS idx_client_person_client_id ON core.client_person(client_id);
CREATE INDEX IF NOT EXISTS idx_client_person_linkedin ON core.client_person(person_linkedin_url);
CREATE INDEX IF NOT EXISTS idx_client_person_company ON core.client_person(company_domain);
CREATE INDEX IF NOT EXISTS idx_client_person_source ON core.client_person(source);
