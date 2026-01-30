-- VC-Backed Companies Missing Customer Data
-- Various queries for finding VC portfolio companies we haven't collected customers for yet
--
-- IMPORTANT: Use CTE approach to avoid statement timeouts on complex JOINs
--
-- Top ~70 VC firms list (update as needed):
--   accel.com, addition.com, altimeter.com, a16z.com, battery.com, bedrockcap.com,
--   benchmark.com, bvp.com, boxgroup.com, coatue.com, compound.vc, craftventures.com,
--   dcvc.com, emcap.com, eniac.vc, fjlabs.com, felicis.com, firstmark.com,
--   firstround.com, forerunnerventures.com, foundationcapital.com, foundercollective.com,
--   foundersfund.com, freestyle.vc, generalatlantic.com, greenoaks.com, ggvc.com, gv.com,
--   generalcatalyst.com, greycroft.com, greylock.com, haystack.vc, industryventures.com,
--   ivp.com, iconiqcapital.com, indexventures.com, initialized.com, insightpartners.com,
--   k9ventures.com, khoslaventures.com, kleinerperkins.com, lererhippeau.com, lsvp.com,
--   luxcapital.com, menlovc.com, nea.com, nextviewventures.com, northzone.com,
--   notablecap.com, operatorpartners.com, pear.vc, primary.vc, quiet.com, redpoint.com,
--   ribbitcap.com, svangel.com, sapphireventures.com, sequoiacap.com, slow.co,
--   soundventures.com, sparkcapital.com, susaventures.com, thrivecap.com, tigerglobal.com,
--   tribecap.co, usv.com, uncorkcapital.com, wischoff.com, sevensevensix.com,
--   salesforceventures.com

--------------------------------------------------------------------------------
-- QUERY 1: Base query - all VC-backed US companies from top VCs, no customers
-- Count: ~2,523 (as of 2026-01-29)
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date, vp.vc_name
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com', 'addition.com', 'altimeter.com', 'a16z.com', 'battery.com',
        'bedrockcap.com', 'benchmark.com', 'bvp.com', 'boxgroup.com', 'coatue.com',
        'compound.vc', 'craftventures.com', 'dcvc.com', 'emcap.com', 'eniac.vc',
        'fjlabs.com', 'felicis.com', 'firstmark.com', 'firstround.com', 'forerunnerventures.com',
        'foundationcapital.com', 'foundercollective.com', 'foundersfund.com', 'freestyle.vc',
        'generalatlantic.com', 'greenoaks.com', 'ggvc.com', 'gv.com', 'generalcatalyst.com',
        'greycroft.com', 'greylock.com', 'haystack.vc', 'industryventures.com', 'ivp.com',
        'iconiqcapital.com', 'indexventures.com', 'initialized.com', 'insightpartners.com',
        'k9ventures.com', 'khoslaventures.com', 'kleinerperkins.com', 'lererhippeau.com',
        'lsvp.com', 'luxcapital.com', 'menlovc.com', 'nea.com', 'nextviewventures.com',
        'northzone.com', 'notablecap.com', 'operatorpartners.com', 'pear.vc', 'primary.vc',
        'quiet.com', 'redpoint.com', 'ribbitcap.com', 'svangel.com', 'sapphireventures.com',
        'sequoiacap.com', 'slow.co', 'soundventures.com', 'sparkcapital.com', 'susaventures.com',
        'thrivecap.com', 'tigerglobal.com', 'tribecap.co', 'usv.com', 'uncorkcapital.com',
        'wischoff.com', 'sevensevensix.com', 'salesforceventures.com'
    )
)
SELECT v.domain, v.name AS company_name, v.linkedin_url, v.vc_name
FROM vc_backed_us v
WHERE NOT EXISTS (
    SELECT 1 FROM core.company_customers cc
    WHERE cc.origin_company_domain = v.domain
)
ORDER BY v.domain;


--------------------------------------------------------------------------------
-- QUERY 2: Founded >= 2019 (strict - excludes NULLs)
-- Uses vc_portfolio.founded_date (text field, regex match)
-- Count: ~962 (as of 2026-01-29)
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date, vp.vc_name
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com', 'addition.com', 'altimeter.com', 'a16z.com', 'battery.com',
        'bedrockcap.com', 'benchmark.com', 'bvp.com', 'boxgroup.com', 'coatue.com',
        'compound.vc', 'craftventures.com', 'dcvc.com', 'emcap.com', 'eniac.vc',
        'fjlabs.com', 'felicis.com', 'firstmark.com', 'firstround.com', 'forerunnerventures.com',
        'foundationcapital.com', 'foundercollective.com', 'foundersfund.com', 'freestyle.vc',
        'generalatlantic.com', 'greenoaks.com', 'ggvc.com', 'gv.com', 'generalcatalyst.com',
        'greycroft.com', 'greylock.com', 'haystack.vc', 'industryventures.com', 'ivp.com',
        'iconiqcapital.com', 'indexventures.com', 'initialized.com', 'insightpartners.com',
        'k9ventures.com', 'khoslaventures.com', 'kleinerperkins.com', 'lererhippeau.com',
        'lsvp.com', 'luxcapital.com', 'menlovc.com', 'nea.com', 'nextviewventures.com',
        'northzone.com', 'notablecap.com', 'operatorpartners.com', 'pear.vc', 'primary.vc',
        'quiet.com', 'redpoint.com', 'ribbitcap.com', 'svangel.com', 'sapphireventures.com',
        'sequoiacap.com', 'slow.co', 'soundventures.com', 'sparkcapital.com', 'susaventures.com',
        'thrivecap.com', 'tigerglobal.com', 'tribecap.co', 'usv.com', 'uncorkcapital.com',
        'wischoff.com', 'sevensevensix.com', 'salesforceventures.com'
    )
)
SELECT v.domain, v.name AS company_name, v.linkedin_url, v.founded_date, v.vc_name
FROM vc_backed_us v
WHERE v.founded_date ~ '201[9]|202[0-6]'
AND NOT EXISTS (
    SELECT 1 FROM core.company_customers cc
    WHERE cc.origin_company_domain = v.domain
)
ORDER BY v.domain;


--------------------------------------------------------------------------------
-- QUERY 3: Founded >= 2019 OR NULL (includes companies with unknown founded date)
-- Recommended for broader coverage
-- Count: ~1,185 (as of 2026-01-29)
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date, vp.vc_name
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com', 'addition.com', 'altimeter.com', 'a16z.com', 'battery.com',
        'bedrockcap.com', 'benchmark.com', 'bvp.com', 'boxgroup.com', 'coatue.com',
        'compound.vc', 'craftventures.com', 'dcvc.com', 'emcap.com', 'eniac.vc',
        'fjlabs.com', 'felicis.com', 'firstmark.com', 'firstround.com', 'forerunnerventures.com',
        'foundationcapital.com', 'foundercollective.com', 'foundersfund.com', 'freestyle.vc',
        'generalatlantic.com', 'greenoaks.com', 'ggvc.com', 'gv.com', 'generalcatalyst.com',
        'greycroft.com', 'greylock.com', 'haystack.vc', 'industryventures.com', 'ivp.com',
        'iconiqcapital.com', 'indexventures.com', 'initialized.com', 'insightpartners.com',
        'k9ventures.com', 'khoslaventures.com', 'kleinerperkins.com', 'lererhippeau.com',
        'lsvp.com', 'luxcapital.com', 'menlovc.com', 'nea.com', 'nextviewventures.com',
        'northzone.com', 'notablecap.com', 'operatorpartners.com', 'pear.vc', 'primary.vc',
        'quiet.com', 'redpoint.com', 'ribbitcap.com', 'svangel.com', 'sapphireventures.com',
        'sequoiacap.com', 'slow.co', 'soundventures.com', 'sparkcapital.com', 'susaventures.com',
        'thrivecap.com', 'tigerglobal.com', 'tribecap.co', 'usv.com', 'uncorkcapital.com',
        'wischoff.com', 'sevensevensix.com', 'salesforceventures.com'
    )
)
SELECT v.domain, v.name AS company_name, v.linkedin_url, v.founded_date, v.vc_name
FROM vc_backed_us v
WHERE (v.founded_date IS NULL OR v.founded_date ~ '201[9]|202[0-6]')
AND NOT EXISTS (
    SELECT 1 FROM core.company_customers cc
    WHERE cc.origin_company_domain = v.domain
)
ORDER BY v.domain;


--------------------------------------------------------------------------------
-- COUNT SUMMARY: Quick stats for all filters
--------------------------------------------------------------------------------
WITH vc_backed_us AS (
    SELECT DISTINCT c.domain, c.name, c.linkedin_url, vp.founded_date, vp.vc_name
    FROM core.companies c
    JOIN extracted.vc_portfolio vp ON vp.domain = c.domain
    JOIN raw.vc_firms vf ON vf.name = vp.vc_name
    JOIN core.company_locations cl ON cl.domain = c.domain AND cl.country = 'United States'
    WHERE vf.domain IN (
        'accel.com', 'addition.com', 'altimeter.com', 'a16z.com', 'battery.com',
        'bedrockcap.com', 'benchmark.com', 'bvp.com', 'boxgroup.com', 'coatue.com',
        'compound.vc', 'craftventures.com', 'dcvc.com', 'emcap.com', 'eniac.vc',
        'fjlabs.com', 'felicis.com', 'firstmark.com', 'firstround.com', 'forerunnerventures.com',
        'foundationcapital.com', 'foundercollective.com', 'foundersfund.com', 'freestyle.vc',
        'generalatlantic.com', 'greenoaks.com', 'ggvc.com', 'gv.com', 'generalcatalyst.com',
        'greycroft.com', 'greylock.com', 'haystack.vc', 'industryventures.com', 'ivp.com',
        'iconiqcapital.com', 'indexventures.com', 'initialized.com', 'insightpartners.com',
        'k9ventures.com', 'khoslaventures.com', 'kleinerperkins.com', 'lererhippeau.com',
        'lsvp.com', 'luxcapital.com', 'menlovc.com', 'nea.com', 'nextviewventures.com',
        'northzone.com', 'notablecap.com', 'operatorpartners.com', 'pear.vc', 'primary.vc',
        'quiet.com', 'redpoint.com', 'ribbitcap.com', 'svangel.com', 'sapphireventures.com',
        'sequoiacap.com', 'slow.co', 'soundventures.com', 'sparkcapital.com', 'susaventures.com',
        'thrivecap.com', 'tigerglobal.com', 'tribecap.co', 'usv.com', 'uncorkcapital.com',
        'wischoff.com', 'sevensevensix.com', 'salesforceventures.com'
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
AND (v.founded_date IS NULL OR v.founded_date ~ '201[9]|202[0-6]')
UNION ALL
SELECT
    'Has NULL founded_date' as filter, COUNT(*) as count
FROM vc_backed_us v
WHERE NOT EXISTS (SELECT 1 FROM core.company_customers cc WHERE cc.origin_company_domain = v.domain)
AND v.founded_date IS NULL;
