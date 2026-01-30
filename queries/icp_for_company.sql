-- ICP Data for a Company
-- Replace 'forethought.ai' with any domain

-- ICP Industries (derived from their customers' industries)
SELECT
    domain,
    icp_industry,
    customer_count
FROM derived.company_icp_industries_from_customers
WHERE domain = 'forethought.ai'
ORDER BY customer_count DESC;

-- ICP Job Titles (derived from their champions' job titles)
SELECT
    domain,
    job_title,
    champion_count
FROM derived.icp_job_titles_from_champions
WHERE domain = 'forethought.ai'
ORDER BY champion_count DESC;
