-- Export company names missing domains for validation
-- Run against main warehouse DB: postgresql://postgres:***@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres

SELECT
    customer_company_name,
    publishing_company_name,
    origin_company_domain,
    case_study_url
FROM extracted.parallel_case_studies
WHERE customer_company_domain IS NULL
  AND customer_company_name IS NOT NULL
  AND customer_company_name <> ''
ORDER BY origin_company_domain, customer_company_name;
