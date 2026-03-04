-- Function to upsert company with COALESCE logic
-- Only fills in name if currently NULL, never overwrites existing name

CREATE OR REPLACE FUNCTION core.upsert_company_coalesce(
    p_domain TEXT,
    p_name TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO core.companies (domain, name)
    VALUES (p_domain, p_name)
    ON CONFLICT (domain) DO UPDATE SET
        name = COALESCE(core.companies.name, EXCLUDED.name),
        updated_at = NOW()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION core.upsert_company_coalesce IS 'Upsert company with COALESCE - only fills name if NULL';
