# Why We Use PostgreSQL Directly (Not Supabase Python Client)

This document explains why AI agents and developers should prefer direct PostgreSQL connections over the Supabase Python client for data warehouse operations, and how to use the PostgreSQL MCP server effectively.

---

## The Problem: Supabase Python Client Limitations

The Supabase Python client (`supabase-py`) wraps PostgREST, which introduces several limitations that became blocking issues during data warehouse work:

### 1. Statement Timeout (Hard-coded ~2 seconds)

PostgREST has a hard-coded statement timeout that **cannot be overridden** from the client side.

```python
# This will timeout on any query taking >2 seconds
result = supabase.from_("large_table").select("*").execute()
```

**Real example from our work:**
- `core.get_leads_by_company_customers()` function takes ~1.5s
- Works fine when tested directly in psql
- Intermittently times out via Supabase client due to PostgREST timeout

### 2. No Transaction Control

The Supabase client executes each query as a separate HTTP request. You cannot:
- Group operations in a transaction
- Use `SET statement_timeout` for a session
- Roll back partial operations

### 3. Large INSERT/UPDATE Limitations

Bulk operations are problematic:

```python
# This fails with statement timeout on large tables
supabase.from_("people").update({"status": "processed"}).eq("batch", 1).execute()
```

**Real example:**
- Needed to insert 355,081 rows into `core.persons_missing_cleaned_title`
- Supabase client timed out repeatedly
- Solution: Direct PostgreSQL with `SET statement_timeout = '10min'`

### 4. No Access to PostgreSQL-Specific Features

PostgREST doesn't expose:
- `EXPLAIN ANALYZE` for query optimization
- `pg_stat_statements` for performance analysis
- Session-level settings
- Advisory locks
- Temp tables

---

## The Solution: Direct PostgreSQL via MCP Server

The `user-postgres` MCP server provides direct PostgreSQL access with full control.

### Connection Details

```
Server: user-postgres
Connection: postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
```

### Key Tools Available

| Tool | Use For |
|------|---------|
| `execute_sql` | Run any SQL query with full timeout control |
| `list_schemas` | Explore database structure |
| `list_objects` | Find tables in a schema |
| `get_object_details` | Get column definitions, indexes, constraints |
| `explain_query` | Analyze query performance |
| `analyze_db_health` | Check for bloated indexes, vacuum needs |

---

## When to Use What

| Operation | Use | Why |
|-----------|-----|-----|
| Simple SELECT with filters | Either | Supabase is convenient for basic queries |
| Bulk INSERT/UPDATE | **PostgreSQL MCP** | Need timeout control |
| Complex queries (>1s) | **PostgreSQL MCP** | Avoid PostgREST timeout |
| PostgreSQL functions | **PostgreSQL MCP** | Full control over execution |
| Schema exploration | **PostgreSQL MCP** | Better introspection tools |
| Data backfills | **PostgreSQL MCP** | Transaction control, timeout settings |
| Quick lookups (<100 rows) | Supabase | Convenient syntax |

---

## Patterns for AI Agents

### Pattern 1: Setting Statement Timeout for Long Operations

```sql
-- Always set timeout before large operations
SET statement_timeout = '10min';

-- Then run the operation
INSERT INTO core.persons_missing_cleaned_title (linkedin_url, raw_job_title)
SELECT linkedin_url, raw_job_title
FROM core.people_full
WHERE matched_cleaned_job_title IS NULL;
```

### Pattern 2: Batched Updates with Progress

```sql
-- Update in batches to avoid locking entire table
WITH batch AS (
  SELECT linkedin_url
  FROM core.person_job_titles
  WHERE matched_job_function IS NULL
  LIMIT 10000
)
UPDATE core.person_job_titles pjt
SET matched_job_function = 'Engineering'
FROM batch
WHERE pjt.linkedin_url = batch.linkedin_url
  AND pjt.matched_cleaned_job_title ILIKE '%engineer%';
```

### Pattern 3: Check Before Bulk Delete

```sql
-- Always count first
SELECT COUNT(*)
FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%barista%';

-- Then delete if count looks right
DELETE FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%barista%';
```

### Pattern 4: Using CTEs for Complex Operations

```sql
-- CTEs are more readable and optimize well
WITH missing_titles AS (
  SELECT linkedin_url, matched_cleaned_job_title
  FROM core.person_job_titles
  WHERE matched_job_function IS NULL
),
engineering_matches AS (
  SELECT linkedin_url
  FROM missing_titles
  WHERE matched_cleaned_job_title ILIKE '%engineer%'
     OR matched_cleaned_job_title ILIKE '%developer%'
)
UPDATE core.person_job_titles pjt
SET matched_job_function = 'Engineering'
FROM engineering_matches em
WHERE pjt.linkedin_url = em.linkedin_url;
```

---

## Specific Guidance for This Data Warehouse

### Schema Organization

| Schema | Purpose | Typical Operations |
|--------|---------|-------------------|
| `raw` | Raw payloads from sources | Read-only (except during ingestion) |
| `extracted` | Flattened/extracted data | Upserts during ingestion |
| `core` | Master entities, dimension tables | Backfills, updates, joins |
| `reference` | Lookup tables | Rarely modified |

### Key Tables for Backfills

```sql
-- People job titles (primary target for job_function/seniority backfills)
core.person_job_titles

-- Company dimension tables (star schema)
core.company_names
core.company_employee_ranges
core.company_types
core.company_locations
core.company_industries
core.company_funding
core.company_revenue

-- Lookup tables for matching
reference.job_title_lookup
reference.employee_range_lookup
reference.industry_lookup
```

### Checking Current State

```sql
-- Lead coverage stats
SELECT
  COUNT(*) as total,
  COUNT(matched_job_function) as has_job_function,
  COUNT(matched_seniority) as has_seniority,
  ROUND(100.0 * COUNT(matched_job_function) / COUNT(*), 1) as job_function_pct,
  ROUND(100.0 * COUNT(matched_seniority) / COUNT(*), 1) as seniority_pct
FROM core.person_job_titles;

-- Company coverage stats
SELECT
  COUNT(DISTINCT domain) as total_companies,
  COUNT(DISTINCT CASE WHEN matched_industry IS NOT NULL THEN domain END) as has_industry
FROM core.company_industries;
```

---

## Anti-Patterns to Avoid

### ❌ Don't: Use Supabase for large operations

```python
# This will timeout
result = supabase.from_("core.person_job_titles").update({
    "matched_job_function": "Engineering"
}).ilike("matched_cleaned_job_title", "%engineer%").execute()
```

### ✅ Do: Use PostgreSQL MCP with timeout

```sql
SET statement_timeout = '5min';
UPDATE core.person_job_titles
SET matched_job_function = 'Engineering'
WHERE matched_job_function IS NULL
  AND matched_cleaned_job_title ILIKE '%engineer%';
```

### ❌ Don't: Run unbounded SELECTs

```sql
-- Will return millions of rows and crash
SELECT * FROM core.leads;
```

### ✅ Do: Always use LIMIT or aggregations

```sql
-- Check sample
SELECT * FROM core.leads LIMIT 10;

-- Or get counts
SELECT COUNT(*) FROM core.leads WHERE matched_industry = 'Software';
```

### ❌ Don't: Delete without counting first

```sql
-- Dangerous: might delete more than expected
DELETE FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%sales%';
```

### ✅ Do: Count, verify, then delete

```sql
-- Step 1: Count
SELECT COUNT(*) FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%sales%';
-- Returns: 45,000

-- Step 2: Verify with sample
SELECT matched_cleaned_job_title FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%sales%' LIMIT 20;

-- Step 3: Delete if count and samples look right
DELETE FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE '%sales%';
```

---

## Summary

| Aspect | Supabase Client | PostgreSQL MCP |
|--------|-----------------|----------------|
| Timeout control | ❌ Hard-coded 2s | ✅ Full control |
| Transaction support | ❌ No | ✅ Yes |
| Bulk operations | ❌ Brittle | ✅ Reliable |
| Schema exploration | ❌ Limited | ✅ Full introspection |
| Quick simple queries | ✅ Convenient | ⚠️ Verbose |
| Use for API layer | ✅ Yes | ❌ No (use asyncpg) |
| Use for data work | ❌ No | ✅ Yes |

**Default choice for AI agents doing data warehouse work: PostgreSQL MCP**

The Supabase Python client is fine for the FastAPI layer serving frontend requests, but for any data engineering, backfills, schema changes, or exploration - use the PostgreSQL MCP server directly.
