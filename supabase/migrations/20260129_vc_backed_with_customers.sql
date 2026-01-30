-- View: VC-backed companies for which we have customer data
-- Shows companies that appear in both VC portfolio and company customers tables

CREATE OR REPLACE VIEW core.vc_backed_with_customers AS
SELECT
    cc.origin_company_domain AS domain,
    cc.origin_company_name AS name,
    COUNT(DISTINCT cc.customer_domain) FILTER (WHERE cc.customer_domain IS NOT NULL) AS customer_count,
    COUNT(DISTINCT cc.customer_name) AS customer_name_count,
    array_agg(DISTINCT vp.vc_name ORDER BY vp.vc_name) AS vc_investors
FROM core.company_customers cc
JOIN extracted.vc_portfolio vp
    ON cc.origin_company_domain = vp.domain
GROUP BY cc.origin_company_domain, cc.origin_company_name;

-- Index to speed up the join
CREATE INDEX IF NOT EXISTS idx_vc_portfolio_domain
    ON extracted.vc_portfolio(domain);

COMMENT ON VIEW core.vc_backed_with_customers IS
    'VC-backed companies for which we have researched their customers. Includes customer count and list of VC investors.';
