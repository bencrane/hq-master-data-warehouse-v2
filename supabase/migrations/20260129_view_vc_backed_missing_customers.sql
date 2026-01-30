-- View: VC-backed US companies that we haven't yet gotten customer data for
-- These are companies from top-tier VCs where core.company_customers has no records

CREATE OR REPLACE VIEW public.vc_backed_missing_customers AS
SELECT DISTINCT
    c.domain,
    c.name as company_name,
    c.linkedin_url,
    vp.vc_name,
    vf.domain as vc_domain
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
AND NOT EXISTS (
    SELECT 1 FROM core.company_customers cc
    WHERE cc.origin_company_domain = c.domain
)
ORDER BY c.domain;

COMMENT ON VIEW public.vc_backed_missing_customers IS
'VC-backed US companies from top-tier VCs that we have not yet enriched with customer data';
