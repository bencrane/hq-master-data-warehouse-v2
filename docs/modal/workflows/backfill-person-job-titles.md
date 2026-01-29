# Backfill Person Job Titles

## Gap Analysis

- `core.people`: 1,465,032
- `core.person_job_titles`: 1,245,673
- **Gap: ~219,359 records**

## Source Tables (in priority order)

| Table | Column | Total | With Title |
|-------|--------|-------|------------|
| `extracted.person_discovery` | `latest_title` | 1,384,074 | 1,383,740 |
| `extracted.person_profile` | `latest_title` | 155,145 | 152,937 |
| `extracted.salesnav_scrapes_person` | `job_title` | 113,334 | 113,334 |
| `extracted.apollo_people_cleaned` | `job_title` | 8,004 | 8,004 |

## Target Table Schema

`core.person_job_titles`:
- `linkedin_url` (TEXT)
- `matched_cleaned_job_title` (TEXT)
- `matched_job_function` (TEXT)
- `matched_seniority` (TEXT)
- `source` (TEXT)

## Lookup Table

`reference.job_title_lookup` - columns: `latest_title`, `cleaned_job_title`, `job_function`, `seniority_level`

## Database Connection

```bash
psql "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"
```

## Steps

### Step 1: Create staging table

```sql
CREATE TABLE staging.person_job_titles AS
SELECT DISTINCT ON (linkedin_url)
  pd.linkedin_url,
  pd.latest_title as raw_title,
  jtl.cleaned_job_title as matched_cleaned_job_title,
  jtl.job_function as matched_job_function,
  jtl.seniority_level as matched_seniority,
  'person_discovery' as source
FROM extracted.person_discovery pd
LEFT JOIN reference.job_title_lookup jtl ON LOWER(pd.latest_title) = LOWER(jtl.latest_title)
WHERE pd.linkedin_url IS NOT NULL
  AND pd.latest_title IS NOT NULL
  AND pd.linkedin_url NOT IN (SELECT linkedin_url FROM core.person_job_titles);
```

### Step 2: Check staging count

```sql
SELECT COUNT(*) FROM staging.person_job_titles;
```

### Step 3: Insert in batches (10k at a time)

```sql
WITH batch AS (
  SELECT linkedin_url, matched_cleaned_job_title, matched_job_function, matched_seniority, source
  FROM staging.person_job_titles
  LIMIT 10000
)
INSERT INTO core.person_job_titles (linkedin_url, matched_cleaned_job_title, matched_job_function, matched_seniority, source)
SELECT * FROM batch
ON CONFLICT (linkedin_url) DO NOTHING;

DELETE FROM staging.person_job_titles
WHERE linkedin_url IN (SELECT linkedin_url FROM core.person_job_titles);
```

Repeat until 0 rows remain.

### Step 4: Verify and cleanup

```sql
SELECT COUNT(*) FROM core.person_job_titles;
SELECT COUNT(*) FROM staging.person_job_titles;  -- should be 0
DROP TABLE staging.person_job_titles;
```

## Status

- [ ] Step 1: Create staging table
- [ ] Step 2: Check staging count
- [ ] Step 3: Insert in batches
- [ ] Step 4: Verify and cleanup
