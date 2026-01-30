-- Add customer_company_domain to existing case_study_champions table

ALTER TABLE extracted.case_study_champions
ADD COLUMN IF NOT EXISTS customer_company_domain TEXT;

CREATE INDEX IF NOT EXISTS idx_case_study_champions_customer_domain
ON extracted.case_study_champions(customer_company_domain);
