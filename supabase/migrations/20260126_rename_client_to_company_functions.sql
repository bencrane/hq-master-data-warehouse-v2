-- Migration: Rename client terminology to company terminology for lead functions
-- Created: 2026-01-26
-- Purpose: Rename get_leads_by_client_customers to get_leads_by_company_customers
--          and add indexes to optimize query performance (fix timeout issues)

-- ============================================
-- STEP 1: Add Performance Indexes
-- These indexes are critical for preventing timeouts
-- ============================================

-- Index on origin_company_domain for filtering by the company whose customers we want
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_company_customers_origin_domain
    ON core.company_customers(origin_company_domain);

-- Index on customer_domain for joining with person_work_history
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_company_customers_customer_domain
    ON core.company_customers(customer_domain);

-- Index on person_work_history for the join (company_domain is used to match customer domains)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_person_work_history_company_domain
    ON core.person_work_history(company_domain);

-- Composite index for the join optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_person_work_history_person_company
    ON core.person_work_history(person_linkedin_url, company_domain);

-- ============================================
-- STEP 2: Create New Core Function
-- ============================================

CREATE OR REPLACE FUNCTION core.get_leads_by_company_customers(
    p_company_domain TEXT,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    lead_id UUID,
    person_linkedin_url TEXT,
    person_name TEXT,
    person_title TEXT,
    current_company_domain TEXT,
    current_company_name TEXT,
    previous_customer_domain TEXT,
    previous_customer_name TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = core, public
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (l.id)
        l.id AS lead_id,
        l.linkedin_url AS person_linkedin_url,
        l.full_name AS person_name,
        l.title AS person_title,
        l.company_domain AS current_company_domain,
        l.company_name AS current_company_name,
        cc.customer_domain AS previous_customer_domain,
        cc.customer_name AS previous_customer_name
    FROM core.leads l
    INNER JOIN core.person_work_history pwh
        ON l.linkedin_url = pwh.person_linkedin_url
    INNER JOIN core.company_customers cc
        ON pwh.company_domain = cc.customer_domain
    WHERE cc.origin_company_domain = p_company_domain
      AND pwh.is_current = FALSE  -- Only past employers
    ORDER BY l.id, pwh.end_date DESC NULLS LAST
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION core.get_leads_by_company_customers(TEXT, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION core.get_leads_by_company_customers(TEXT, INTEGER, INTEGER) TO service_role;

-- Add function comment
COMMENT ON FUNCTION core.get_leads_by_company_customers IS
'Finds leads who previously worked at customers of a given company.
Parameters:
  - p_company_domain: The domain of the company whose customers'' former employees we want to find
  - p_limit: Maximum number of results (default 100)
  - p_offset: Number of results to skip for pagination (default 0)
Returns leads with their current info and the customer company they previously worked at.';

-- ============================================
-- STEP 3: Create Public Wrapper Function
-- ============================================

CREATE OR REPLACE FUNCTION public.get_leads_by_company_customers(
    p_company_domain TEXT,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    lead_id UUID,
    person_linkedin_url TEXT,
    person_name TEXT,
    person_title TEXT,
    current_company_domain TEXT,
    current_company_name TEXT,
    previous_customer_domain TEXT,
    previous_customer_name TEXT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, core
AS $$
    SELECT * FROM core.get_leads_by_company_customers(p_company_domain, p_limit, p_offset);
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.get_leads_by_company_customers(TEXT, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_leads_by_company_customers(TEXT, INTEGER, INTEGER) TO service_role;
GRANT EXECUTE ON FUNCTION public.get_leads_by_company_customers(TEXT, INTEGER, INTEGER) TO anon;

-- Add function comment
COMMENT ON FUNCTION public.get_leads_by_company_customers IS
'Public wrapper for core.get_leads_by_company_customers.
Finds leads who previously worked at customers of a given company.';

-- ============================================
-- STEP 4: Drop Old Functions (if they exist)
-- ============================================

-- Drop public wrapper first (depends on core function)
DROP FUNCTION IF EXISTS public.get_leads_by_client_customers(TEXT, INTEGER, INTEGER);

-- Drop core function
DROP FUNCTION IF EXISTS core.get_leads_by_client_customers(TEXT, INTEGER, INTEGER);

-- ============================================
-- STEP 5: Additional Index for Leads Table
-- ============================================

-- Index on leads linkedin_url for the join with person_work_history
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_leads_linkedin_url
    ON core.leads(linkedin_url);
