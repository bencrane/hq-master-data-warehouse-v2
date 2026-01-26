-- Migration: Sales Nav Industries Reference
-- Description: Reference table for Sales Navigator industry names

CREATE TABLE IF NOT EXISTS reference.sales_nav_industries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'sales_navigator',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (name, source)
);

CREATE INDEX IF NOT EXISTS idx_sales_nav_industries_name ON reference.sales_nav_industries(name);
CREATE INDEX IF NOT EXISTS idx_sales_nav_industries_source ON reference.sales_nav_industries(source);

-- Populate with Sales Navigator industries
INSERT INTO reference.sales_nav_industries (name, source) VALUES
    ('Advertising Services', 'sales_navigator'),
    ('Banking', 'sales_navigator'),
    ('Consumer Goods', 'sales_navigator'),
    ('Cosmetics', 'sales_navigator'),
    ('Financial Services', 'sales_navigator'),
    ('Food & Beverages', 'sales_navigator'),
    ('Internet Marketplace Platforms', 'sales_navigator'),
    ('Law Practice', 'sales_navigator'),
    ('Retail', 'sales_navigator'),
    ('Software Development', 'sales_navigator'),
    ('Staffing and Recruiting', 'sales_navigator'),
    ('Technology, Information and Internet', 'sales_navigator'),
    ('Technology, Information and Media', 'sales_navigator')
ON CONFLICT (name, source) DO NOTHING;
