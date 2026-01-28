# Backfill Company Descriptions

## Overview

Backfills `core.company_descriptions` by coalescing descriptions from multiple source tables with priority ordering.

## Priority Order

1. **vc_portfolio** (`long_description`) - highest priority
2. **company_firmographics** (`description`)
3. **company_discovery** (`description`) - lowest priority

## Source Tables

| Table | Schema | Description Field | Unique Domains |
|-------|--------|-------------------|----------------|
| `extracted.vc_portfolio` | extracted | `long_description` | ~7,625 |
| `extracted.company_firmographics` | extracted | `description` | ~39,088 (new) |
| `extracted.company_discovery` | extracted | `description` | ~450,164 (new) |

**Total: ~496,877 unique companies with descriptions**

## Target Table

**`core.company_descriptions`**

| Column | Type | Description |
|--------|------|-------------|
| domain | TEXT | Company domain (unique) |
| description | TEXT | Coalesced description |
| tagline | TEXT | Short tagline (if available) |
| source | TEXT | Which source the description came from |

## Database Connection

```bash
psql "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"
```

## Steps (SQL-based approach)

### Step 1: Insert from vc_portfolio (highest priority)

Run once:

```sql
INSERT INTO core.company_descriptions (domain, description, source)
SELECT DISTINCT ON (domain)
  domain,
  long_description,
  'vc_portfolio'
FROM extracted.vc_portfolio
WHERE domain IS NOT NULL AND long_description IS NOT NULL
ON CONFLICT (domain) DO UPDATE SET
  description = EXCLUDED.description,
  source = EXCLUDED.source;
```

### Step 2: Insert from company_firmographics

Run once:

```sql
INSERT INTO core.company_descriptions (domain, description, source)
SELECT DISTINCT ON (company_domain)
  company_domain,
  description,
  'company_firmographics'
FROM extracted.company_firmographics
WHERE company_domain IS NOT NULL AND description IS NOT NULL
ON CONFLICT (domain) DO NOTHING;
```

### Step 3: Create staging table for company_discovery

The company_discovery table has ~450k rows, which times out with direct queries. Use a staging table:

```sql
CREATE TABLE core.company_descriptions_staging AS
SELECT DISTINCT ON (domain)
  domain,
  description,
  'company_discovery' as source
FROM extracted.company_discovery
WHERE domain IS NOT NULL
  AND description IS NOT NULL
  AND domain NOT IN (SELECT domain FROM core.company_descriptions);
```

### Step 4: Check staging row count

```sql
SELECT COUNT(*) FROM core.company_descriptions_staging;
```

Expected: ~450,000 rows

### Step 5: Insert in batches from staging

Run repeatedly until 0 rows remain:

```sql
WITH batch AS (
  SELECT domain, description, source
  FROM core.company_descriptions_staging
  LIMIT 10000
)
INSERT INTO core.company_descriptions (domain, description, source)
SELECT * FROM batch
ON CONFLICT (domain) DO NOTHING;

DELETE FROM core.company_descriptions_staging
WHERE domain IN (SELECT domain FROM core.company_descriptions);
```

### Step 6: Verify completion

```sql
SELECT COUNT(*) FROM core.company_descriptions;
SELECT COUNT(*) FROM core.company_descriptions_staging;  -- should be 0
SELECT source, COUNT(*) FROM core.company_descriptions GROUP BY source;
```

### Step 7: Clean up staging table

```sql
DROP TABLE core.company_descriptions_staging;
```

## Modal Function (Alternative)

**Endpoint:** `backfill_company_descriptions`

**URL:** `https://bencrane--hq-master-data-ingest-backfill-company-descriptions.modal.run`

**Method:** POST

**Payload:**
```json
{
  "batch_size": 1000,
  "dry_run": false
}
```

Note: The Modal function works for small batches but the SQL approach above is faster for bulk backfill.

## Files

| File | Purpose |
|------|---------|
| `modal-mcp-server/src/ingest/backfill_company_descriptions.py` | Modal endpoint |
| `docs/modal/workflows/backfill-company-descriptions.md` | This doc |

## Status

- [x] Step 1: Insert from vc_portfolio
- [x] Step 2: Insert from company_firmographics
- [ ] Step 3: Create staging table for company_discovery
- [ ] Step 4: Check staging row count
- [ ] Step 5: Insert in batches from staging
- [ ] Step 6: Verify completion
- [ ] Step 7: Clean up staging table
