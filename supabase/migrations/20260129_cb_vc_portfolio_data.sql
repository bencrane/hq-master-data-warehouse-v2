-- CB VC Portfolio Data: stores Crunchbase VC portfolio company data

-- Raw table: stores the full payload
CREATE TABLE raw.cb_vc_portfolio_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    domain TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    short_description TEXT,
    employee_range TEXT,
    last_funding_date TEXT,
    last_funding_type TEXT,
    last_funding_amount TEXT,
    last_equity_funding_type TEXT,
    last_leadership_hiring_date TEXT,
    founded_date TEXT,
    estimated_revenue_range TEXT,
    funding_status TEXT,
    total_funding_amount TEXT,
    total_equity_funding_amount TEXT,
    operating_status TEXT,
    company_linkedin_url TEXT,
    vc TEXT,
    vc1 TEXT,
    vc2 TEXT,
    vc3 TEXT,
    vc4 TEXT,
    vc5 TEXT,
    vc6 TEXT,
    vc7 TEXT,
    vc8 TEXT,
    vc9 TEXT,
    vc10 TEXT,
    vc11 TEXT,
    vc12 TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extracted table: one row per VC-company relationship (exploded from vc columns)
CREATE TABLE extracted.cb_vc_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.cb_vc_portfolio_payloads(id),
    company_name TEXT NOT NULL,
    domain TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    short_description TEXT,
    employee_range TEXT,
    last_funding_date TEXT,
    last_funding_type TEXT,
    last_funding_amount TEXT,
    last_equity_funding_type TEXT,
    last_leadership_hiring_date TEXT,
    founded_date TEXT,
    estimated_revenue_range TEXT,
    funding_status TEXT,
    total_funding_amount TEXT,
    total_equity_funding_amount TEXT,
    operating_status TEXT,
    company_linkedin_url TEXT,
    vc_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_cb_vc_portfolio_payloads_domain ON raw.cb_vc_portfolio_payloads(domain);
CREATE INDEX idx_cb_vc_portfolio_domain ON extracted.cb_vc_portfolio(domain);
CREATE INDEX idx_cb_vc_portfolio_vc_name ON extracted.cb_vc_portfolio(vc_name);
CREATE INDEX idx_cb_vc_portfolio_company_name ON extracted.cb_vc_portfolio(company_name);

COMMENT ON TABLE raw.cb_vc_portfolio_payloads IS 'Raw Crunchbase VC portfolio company data payloads';
COMMENT ON TABLE extracted.cb_vc_portfolio IS 'Exploded VC-company relationships from Crunchbase data - one row per VC';
