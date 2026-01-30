-- VC-Backed Companies Missing Customer Data
--
-- PURPOSE: Find companies that:
--   1. Are located in the United States
--   2. Raised money from one of our ~70 top-tier VCs (a16z, Sequoia, Greylock, etc.)
--   3. Do NOT yet have customer data in core.company_customers
--
-- USE CASE: Identify high-quality companies to collect customer/testimonial data for
--
-- TABLES USED:
--   - core.companies: company master data
--   - extracted.vc_portfolio: VC portfolio company relationships
--   - raw.vc_firms: list of VC firms with their domains
--   - core.company_locations: company location (filtered to US)
--   - core.company_customers: existing customer data (used for exclusion)
--
-- NOTE: Uses CTE approach to avoid statement timeouts on complex JOINs

--------------------------------------------------------------------------------
-- COUNT QUERY: How many VC-backed US companies are missing customer data?
-- As of 2026-01-29: ~2,523 total, ~962 founded 2019+, ~1,185 including NULL
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com','addition.com','altimeter.com','a16z.com','battery.com','bedrockcap.com',
        'benchmark.com','bvp.com','boxgroup.com','coatue.com','compound.vc','craftventures.com',
        'dcvc.com','emcap.com','eniac.vc','fjlabs.com','felicis.com','firstmark.com',
        'firstround.com','forerunnerventures.com','foundationcapital.com','foundercollective.com',
        'foundersfund.com','freestyle.vc','generalatlantic.com','greenoaks.com','ggvc.com','gv.com',
        'generalcatalyst.com','greycroft.com','greylock.com','haystack.vc','industryventures.com',
        'ivp.com','iconiqcapital.com','indexventures.com','initialized.com','insightpartners.com',
        'k9ventures.com','khoslaventures.com','kleinerperkins.com','lererhippeau.com','lsvp.com',
        'luxcapital.com','menlovc.com','nea.com','nextviewventures.com','northzone.com',
        'notablecap.com','operatorpartners.com','pear.vc','primary.vc','quiet.com','redpoint.com',
        'ribbitcap.com','svangel.com','sapphireventures.com','sequoiacap.com','slow.co',
        'soundventures.com','sparkcapital.com','susaventures.com','thrivecap.com','tigerglobal.com',
        'tribecap.co','usv.com','uncorkcapital.com','wischoff.com','sevensevensix.com',
        'salesforceventures.com'
    )
)
SELECT
    'Total missing customers' as filter, COUNT(*) as count
FROM vc_backed_us v
WHERE NOT EXISTS (SELECT 1 FROM core.company_customers cc WHERE cc.origin_company_domain = v.domain)
UNION ALL
SELECT
    'Founded 2019+ (strict)' as filter, COUNT(*) as count
FROM vc_backed_us v
WHERE NOT EXISTS (SELECT 1 FROM core.company_customers cc WHERE cc.origin_company_domain = v.domain)
AND v.founded_date ~ '201[9]|202[0-6]'
UNION ALL
SELECT
    'Founded 2019+ OR NULL' as filter, COUNT(*) as count
FROM vc_backed_us v
WHERE NOT EXISTS (SELECT 1 FROM core.company_customers cc WHERE cc.origin_company_domain = v.domain)
AND (v.founded_date IS NULL OR v.founded_date ~ '201[9]|202[0-6]');

--------------------------------------------------------------------------------
-- FULL DATA QUERY: Get domain, company name, and LinkedIn URL (Founded 2019+ OR NULL)
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com','addition.com','altimeter.com','a16z.com','battery.com','bedrockcap.com',
        'benchmark.com','bvp.com','boxgroup.com','coatue.com','compound.vc','craftventures.com',
        'dcvc.com','emcap.com','eniac.vc','fjlabs.com','felicis.com','firstmark.com',
        'firstround.com','forerunnerventures.com','foundationcapital.com','foundercollective.com',
        'foundersfund.com','freestyle.vc','generalatlantic.com','greenoaks.com','ggvc.com','gv.com',
        'generalcatalyst.com','greycroft.com','greylock.com','haystack.vc','industryventures.com',
        'ivp.com','iconiqcapital.com','indexventures.com','initialized.com','insightpartners.com',
        'k9ventures.com','khoslaventures.com','kleinerperkins.com','lererhippeau.com','lsvp.com',
        'luxcapital.com','menlovc.com','nea.com','nextviewventures.com','northzone.com',
        'notablecap.com','operatorpartners.com','pear.vc','primary.vc','quiet.com','redpoint.com',
        'ribbitcap.com','svangel.com','sapphireventures.com','sequoiacap.com','slow.co',
        'soundventures.com','sparkcapital.com','susaventures.com','thrivecap.com','tigerglobal.com',
        'tribecap.co','usv.com','uncorkcapital.com','wischoff.com','sevensevensix.com',
        'salesforceventures.com'
    )
)
SELECT v.domain, v.name as company_name, v.linkedin_url, v.founded_date
FROM vc_backed_us v
WHERE (v.founded_date IS NULL OR v.founded_date ~ '201[9]|202[0-6]')
AND NOT EXISTS (
    SELECT 1 FROM core.company_customers cc
    WHERE cc.origin_company_domain = v.domain
)
ORDER BY v.domain;
