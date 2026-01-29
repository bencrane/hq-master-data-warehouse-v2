-- USA Public Companies with Domains

-- Count query
SELECT COUNT(DISTINCT cd.domain) as usa_public_companies
FROM extracted.company_discovery cd
JOIN core.company_locations cl ON cl.domain = cd.domain
WHERE cd.type = 'Public Company'
  AND cl.country = 'United States'
  AND cd.domain IS NOT NULL;

-- Full data query
SELECT DISTINCT cd.domain
FROM extracted.company_discovery cd
JOIN core.company_locations cl ON cl.domain = cd.domain
WHERE cd.type = 'Public Company'
  AND cl.country = 'United States'
  AND cd.domain IS NOT NULL
ORDER BY cd.domain;
