-- Staffing Parallel AI Tables
-- Created retroactively to document tables that already exist in production

-- =============================================================================
-- API Response Format Tables (for raw /search endpoint responses)
-- =============================================================================

-- Raw payload storage for Parallel AI search API responses
CREATE TABLE IF NOT EXISTS raw.staffing_parallel_search_payloads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain text NOT NULL,
    company_name text,
    objective text,
    payload jsonb NOT NULL,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_staffing_parallel_search_domain
    ON raw.staffing_parallel_search_payloads(domain);

-- Extracted search results
CREATE TABLE IF NOT EXISTS extracted.staffing_parallel_search (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    domain text NOT NULL,
    company_name text,
    search_id text,
    result_count integer,
    urls text[],
    excerpts_summary text,
    raw_payload_id uuid REFERENCES raw.staffing_parallel_search_payloads(id),
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_staffing_parallel_search_domain
    ON extracted.staffing_parallel_search(domain);

-- =============================================================================
-- V1 Tables - Structured Job Search Output (for web UI JSON exports)
-- =============================================================================

-- Raw payload storage for structured job search JSON
CREATE TABLE IF NOT EXISTS raw.staffing_parallel_job_search_v1_payloads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    search_name text,
    input_objective text,
    input_queries text[],
    payload jsonb NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- Search-level metadata and market overview
CREATE TABLE IF NOT EXISTS extracted.staffing_parallel_job_search_v1 (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id uuid REFERENCES raw.staffing_parallel_job_search_v1_payloads(id),
    search_name text,
    market_overview text,
    job_posting_count integer,
    skill_trend_count integer,
    created_at timestamptz DEFAULT now()
);

-- Individual job postings extracted from search
CREATE TABLE IF NOT EXISTS extracted.staffing_parallel_job_postings_v1 (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id uuid REFERENCES extracted.staffing_parallel_job_search_v1(id),
    company_name text,
    job_title text,
    location text,
    salary_range text,
    equity_offered boolean,
    key_responsibilities text,
    required_technologies text,
    experience_level text,
    posting_url text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_staffing_job_postings_v1_search
    ON extracted.staffing_parallel_job_postings_v1(search_id);
CREATE INDEX IF NOT EXISTS idx_staffing_job_postings_v1_company
    ON extracted.staffing_parallel_job_postings_v1(company_name);

-- Skill trends identified in the market
CREATE TABLE IF NOT EXISTS extracted.staffing_parallel_skill_trends_v1 (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    search_id uuid REFERENCES extracted.staffing_parallel_job_search_v1(id),
    skill_category text,
    technologies text,
    description text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_staffing_skill_trends_v1_search
    ON extracted.staffing_parallel_skill_trends_v1(search_id);
