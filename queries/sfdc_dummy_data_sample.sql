-- =============================================
-- QUERY 1: ACCOUNTS
-- =============================================

SELECT
    name,
    website,
    industry,
    NULL AS phone,
    city AS billing_city,
    state AS billing_state
FROM extracted.company_firmographics
WHERE company_domain IN (
    'vanta.com',
    'podium.com',
    'gong.io',
    'outreach.io',
    'salesloft.com',
    'drift.com',
    'segment.com',
    'figma.com',
    'notion.so',
    'airtable.com',
    'zapier.com',
    'calendly.com'
);


-- =============================================
-- QUERY 2: CONTACTS (4-5 per company)
-- =============================================

WITH ranked_contacts AS (
    SELECT
        p.first_name,
        p.last_name,
        p.latest_title AS title,
        c.name AS account_name,
        ROW_NUMBER() OVER (PARTITION BY c.company_domain ORDER BY p.latest_title) AS rn
    FROM extracted.person_profile p
    JOIN extracted.company_firmographics c ON p.latest_company_domain = c.company_domain
    WHERE c.company_domain IN (
        'vanta.com',
        'podium.com',
        'gong.io',
        'outreach.io',
        'salesloft.com',
        'drift.com',
        'segment.com',
        'figma.com',
        'notion.so',
        'airtable.com',
        'zapier.com',
        'calendly.com'
    )
    AND p.latest_title ILIKE ANY(ARRAY['%growth%','%marketing%','%sales%','%revenue%','%demand%','%gtm%','%vp%','%director%','%head of%'])
)
SELECT
    first_name,
    last_name,
    NULL AS email,
    title,
    NULL AS phone,
    account_name
FROM ranked_contacts
WHERE rn <= 5
ORDER BY account_name, title;
