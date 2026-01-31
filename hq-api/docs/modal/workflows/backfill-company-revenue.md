# Backfill Company Revenue

## Overview

Populates `core.company_revenue` with annual revenue ranges from `extracted.company_discovery`.

## Source Data

| Table | Field | Records with Data |
|-------|-------|-------------------|
| `extracted.company_discovery` | `annual_revenue` | ~485,000 |

**Revenue Range Values:**
- 0-500K
- 500K-1M
- 1M-5M
- 5M-10M
- 10M-25M
- 25M-75M
- 75M-200M
- 200M-500M
- 500M-1B
- 1B-10B
- 10B-100B
- 100B-1T

## Target Table

**`core.company_revenue`**

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| domain | TEXT | Company domain (unique) |
| annual_revenue | TEXT | Revenue range string |
| created_at | TIMESTAMPTZ | When record was created |

## Database Connection

```bash
psql "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"
```

## Steps

### Step 1: Create the table (DONE)

```sql
CREATE TABLE IF NOT EXISTS core.company_revenue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL UNIQUE,
    annual_revenue TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_revenue_domain ON core.company_revenue(domain);

GRANT SELECT ON core.company_revenue TO anon, authenticated;
GRANT ALL ON core.company_revenue TO service_role;
```

### Step 2: Create staging table

This avoids timeout issues by pre-computing the distinct domains.

```sql
CREATE TABLE core.company_revenue_staging AS
SELECT DISTINCT ON (domain)
  domain,
  annual_revenue
FROM extracted.company_discovery
WHERE domain IS NOT NULL
  AND annual_revenue IS NOT NULL;
```

### Step 3: Check row count

```sql
SELECT COUNT(*) FROM core.company_revenue_staging;
```

Expected: ~485,000 rows

### Step 4: Insert in batches

Run this repeatedly until it returns 0 rows inserted:

```sql
WITH batch AS (
  SELECT domain, annual_revenue
  FROM core.company_revenue_staging
  LIMIT 10000
)
INSERT INTO core.company_revenue (domain, annual_revenue)
SELECT * FROM batch
ON CONFLICT (domain) DO NOTHING;

DELETE FROM core.company_revenue_staging
WHERE domain IN (SELECT domain FROM core.company_revenue);
```

### Step 5: Verify completion

```sql
SELECT COUNT(*) FROM core.company_revenue;
SELECT COUNT(*) FROM core.company_revenue_staging;  -- should be 0
```

### Step 6: Clean up staging table

```sql
DROP TABLE core.company_revenue_staging;
```

## Files

| File | Purpose |
|------|---------|
| `supabase/migrations/20260128_core_company_revenue.sql` | Table creation migration |
| `docs/modal/workflows/backfill-company-revenue.md` | This doc |

## Status

- [x] Step 1: Create table
- [ ] Step 2: Create staging table
- [ ] Step 3: Check row count
- [ ] Step 4: Insert in batches
- [ ] Step 5: Verify completion
- [ ] Step 6: Clean up staging table
