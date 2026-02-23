-- Add customer domain resolution columns to company_customer_claygent
-- Created: 2026-02-16

ALTER TABLE extracted.company_customer_claygent
ADD COLUMN IF NOT EXISTS company_customer_domain TEXT,
ADD COLUMN IF NOT EXISTS domain_match_source TEXT;

CREATE INDEX IF NOT EXISTS idx_company_customer_claygent_customer_domain
ON extracted.company_customer_claygent(company_customer_domain)
WHERE company_customer_domain IS NOT NULL;

COMMENT ON COLUMN extracted.company_customer_claygent.company_customer_domain IS 'Resolved domain for customer company';
COMMENT ON COLUMN extracted.company_customer_claygent.domain_match_source IS 'How domain was resolved (e.g., db-exact-name-match)';
