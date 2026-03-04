-- Atomic upsert for company name with COALESCE logic:
-- - Insert if domain doesn't exist
-- - Update name only if existing name is NULL
-- - Do nothing if name already set

CREATE OR REPLACE FUNCTION core.upsert_company_name_if_null(p_domain text, p_name text)
RETURNS void AS $$
  INSERT INTO core.companies (domain, name)
  VALUES (p_domain, p_name)
  ON CONFLICT (domain) DO UPDATE
  SET name = EXCLUDED.name
  WHERE core.companies.name IS NULL;
$$ LANGUAGE sql;
