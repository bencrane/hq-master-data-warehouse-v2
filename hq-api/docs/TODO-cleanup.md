# Data Cleanup TODO (Non-Urgent)

These items are non-urgent because the affected records are already hidden from the dashboard via API filters.

---

## Companies

### Delete companies with no location data
- **Table:** `core.companies_missing_location`
- **Count:** ~55,000 companies
- **Criteria:** `discovery_location IS NULL AND salesnav_location IS NULL`
- **Why non-urgent:** API requires `company_country` - these leads don't show up anyway
- **SQL (run in small batches):**
```sql
DELETE FROM core.companies
WHERE id IN (
    SELECT id
    FROM core.companies_missing_location
    WHERE discovery_location IS NULL
      AND salesnav_location IS NULL
    LIMIT 100
);
```

---

## People

### Backfill person_tenure with new start dates
- **Table:** `core.person_job_start_dates` has 4,858 people not in `core.person_tenure`
- **Action:** Insert these into person_tenure
- **Why created:** Apollo InstantData "new in role" + SalesNav + person_profile start dates

---

## Reference Tables to Clean

### companies_missing_cleaned_name
- Created for Clay enrichment
- Can delete after enrichment complete

### people_missing_country
- Created for reviewing people without country
- Can delete after backfill complete

---

## Funding Data

### Backfill core.company_funding from extracted.company_discovery
- **Source:** `extracted.company_discovery.total_funding_amount_range_usd`
- **Target:** `core.company_funding`
- **Delta:** ~96,000 companies with funding data not yet in core
- **Issue:** Direct INSERT with JOIN times out due to table size
- **Plan:** Create intermediate table first, then batch insert
- **SQL approach:**
```sql
-- Step 1: Create intermediate table with delta
CREATE TABLE public.funding_backfill AS
SELECT DISTINCT ON (e.domain)
    e.domain,
    e.total_funding_amount_range_usd as raw_funding_range
FROM extracted.company_discovery e
LEFT JOIN core.company_funding cf ON cf.domain = e.domain
WHERE e.total_funding_amount_range_usd IS NOT NULL
  AND cf.domain IS NULL;

-- Step 2: Batch insert from intermediate table
INSERT INTO core.company_funding (domain, raw_funding_range, source)
SELECT domain, raw_funding_range, 'extracted.company_discovery'
FROM public.funding_backfill
LIMIT 5000 OFFSET 0;

-- Step 3: Drop when done
DROP TABLE public.funding_backfill;
```

---

## Job Function Data

### Fix line breaks in matched_job_function
- **Table:** `core.person_job_titles`
- **Column:** `matched_job_function`
- **Count:** ~15,208 records with `\n` line breaks
- **Examples:**
  - `'Marketing \n  and Public Relations'` → `'Marketing and Public Relations'`
  - `'Science   \n  and Research'` → `'Science and Research'`
  - `'Human     \n  Resources and Recruiting'` → `'Human Resources and Recruiting'`
- **SQL:**
```sql
UPDATE core.person_job_titles
SET matched_job_function = TRIM(REGEXP_REPLACE(matched_job_function, E'[\\s\\n]+', ' ', 'g'))
WHERE matched_job_function LIKE E'%\n%';
```

---

## Notes

- API required fields: `company_name`, `company_country`, `person_country`, `matched_job_function`, `matched_seniority`
- Records missing any of these are automatically hidden from dashboard
- Focus enrichment efforts on filling these gaps to increase visible lead count
