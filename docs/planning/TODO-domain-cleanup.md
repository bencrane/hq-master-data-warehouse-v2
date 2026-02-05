# TODO: Domain Cleanup & Normalization

## Completed (2026-02-05)

Cleaned 238 dirty `customer_domain` values in `core.company_customers`:
- Stripped `http://` and `https://` prefixes (153 rows)
- Stripped paths like `/info/vmware`, `/fuze`, `/home.html` (48 rows)
- Stripped query params (e.g., `?utm_campaign=...`)
- Stripped `www.` prefix (29 rows)
- Lowercased (e.g., `Figma.com` -> `figma.com`) (44 rows)
- Trimmed whitespace (1 row)

## Still Outstanding

### 1. Non-domain garbage in `customer_domain` (37 rows)

37 rows in `core.company_customers` have people's names or categories in the `customer_domain` column instead of actual domains. These came from upstream extraction (likely Clay or case study parsing) that put the wrong field into `customer_domain`.

Examples:
- `Armon Dadgar` (customer_name = HashiCorp)
- `Cheng Zou` (customer_name = Zuora) — 5 duplicate rows
- `Evan Cooke` (customer_name = Twilio) — 11 duplicate rows
- `Corporate Venture Capital` (customer_name = Slack)
- `CRM` (customer_name = Woflow)
- `Developer Tools` (customer_name = Ockam)
- `Internet` (customer_name = Voiceflow)

**Action needed**: Delete these rows or fix the domain. The customer_name is correct but the domain is wrong. Could look up real domains from `core.companies` by name.

Query to find them:
```sql
SELECT customer_domain, customer_name, origin_company_domain
FROM core.company_customers
WHERE customer_domain !~ '\.' AND customer_domain ~ '[A-Z]';
```

### 2. Ingest-layer normalization

The cleanup above was a one-time fix on existing data. We need to prevent dirty domains from being ingested in the future. Endpoints that write to `customer_domain` should normalize at ingest time:

- Strip protocol (`http://`, `https://`)
- Strip `www.`
- Strip path and query params
- Lowercase
- Trim whitespace

Affected ingest endpoints to audit:
- `ingest_company_customers_claygent`
- `ingest_company_customers_structured`
- `ingest_company_customers_v2`
- `resolve_customer_domain`
- Any case study extraction that writes customer domains

### 3. Audit other domain columns across the DB

The same dirty-domain problem likely exists in other tables. Columns to audit:
- `core.companies.domain`
- `core.company_customers.origin_company_domain`
- `extracted.*.domain` columns
- `core.company_similar_companies_preview.company_domain`
- Any other `*_domain` column

Query pattern to check any table:
```sql
SELECT column_name
FROM core.table_name
WHERE column_name ~ '^https?://'
   OR column_name ~ '[A-Z]'
   OR column_name ~ '\?'
   OR column_name ~ '/'
   OR column_name ~ '^www\.'
LIMIT 10;
```
