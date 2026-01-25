# VC Portfolio Companies Cleanup Plan

## Table Clarification

| Table | Records | Status |
|-------|---------|--------|
| `raw.vc_portfolio_companies` | ~17k | **Older/malformed** - has shifted column issues |
| `raw.vc_portfolio_payloads` → `extracted.vc_portfolio` | ~7.4k | **Newer/correct** - this is the active pipeline |

The `extracted.vc_portfolio` table is the one being actively used and pushed to. The `raw.vc_portfolio_companies` table is legacy data with quality issues.

---

## Problem Summary

The `raw.vc_portfolio_companies` table has **17,230 records** across 62 uploads. Approximately half have **shifted/misaligned columns** due to inconsistent CSV imports.

### Good Uploads (~9,000 records)
- Proper data in all fields
- `linkedin_url` contains actual LinkedIn URLs
- `city`, `state`, `country` contain location strings
- `revenue_range` contains revenue data

### Bad Uploads (~8,000 records)
- Columns are shifted
- `city`, `state`, `country` = Crunchbase URLs
- `employee_count` = Crunchbase URL
- `linkedin_url` = Revenue data (e.g., "$500M to $1B")
- `revenue_range`, `funding_total`, `equity_funding` = Crunchbase URLs

## Identifying Good vs Bad Uploads

```sql
-- Good uploads: linkedin_url starts with https://www.linkedin
-- Bad uploads: city starts with https://

SELECT upload_id,
  CASE WHEN city LIKE 'https://%' THEN 'BAD' ELSE 'GOOD' END as status,
  COUNT(*) as cnt
FROM raw.vc_portfolio_companies
GROUP BY upload_id, CASE WHEN city LIKE 'https://%' THEN 'BAD' ELSE 'GOOD' END;
```

## Recommended Approach

### Option 1: Keep Only Good Uploads (Simplest)

1. Identify good upload_ids:
```sql
SELECT DISTINCT upload_id
FROM raw.vc_portfolio_companies
WHERE city NOT LIKE 'https://%';
```

2. Create cleaned table or delete bad records:
```sql
DELETE FROM raw.vc_portfolio_companies
WHERE city LIKE 'https://%';
```

3. Clean remaining data:
   - Strip trailing `/` from `website_domain`
   - Strip trailing `/` and `/admin/` from `linkedin_url`
   - Normalize numeric LinkedIn IDs if possible

### Option 2: Attempt Column Shift Fix (Risky)

For bad uploads, the data appears shifted. Would need to:
1. Identify exact shift pattern per upload
2. Move data from wrong columns to correct ones
3. Risk: May not be recoverable if data was truncated

### Option 3: Re-import from Source

If original CSVs are available with correct column mappings, re-import the bad uploads.

## Data Quality Fixes (After Cleanup)

```sql
-- Strip trailing / from domains
UPDATE raw.vc_portfolio_companies
SET website_domain = RTRIM(website_domain, '/')
WHERE website_domain LIKE '%/';

-- Strip trailing / from LinkedIn URLs
UPDATE raw.vc_portfolio_companies
SET linkedin_url = RTRIM(linkedin_url, '/')
WHERE linkedin_url LIKE '%/';

-- Strip /admin/ from LinkedIn URLs
UPDATE raw.vc_portfolio_companies
SET linkedin_url = REPLACE(linkedin_url, '/admin/', '')
WHERE linkedin_url LIKE '%/admin/%';
```

## Final Validation

After cleanup, verify:
```sql
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN website_domain NOT LIKE '%/' THEN 1 END) as clean_domains,
  COUNT(CASE WHEN linkedin_url LIKE 'https://www.linkedin.com/company/%' THEN 1 END) as valid_linkedin,
  COUNT(CASE WHEN city NOT LIKE 'https://%' THEN 1 END) as valid_city
FROM raw.vc_portfolio_companies;
```

## Priority

**LOW** - Seniority work is more critical. Return to this cleanup later.

---

*Created: 2026-01-25*
