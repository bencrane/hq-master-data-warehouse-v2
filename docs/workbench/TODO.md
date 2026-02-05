# TODO - Master Task List

Single source of truth for all pending work.

---

## High Priority

### CRITICAL: origin_company_name null when sending case study URLs to Clay
**Status:** Unresolved — needs root cause diagnosis and fix
**Date:** 2026-02-04

**Problem:** 1,040 rows in `raw.staging_case_study_urls` had `origin_company_name = NULL`. 851 were sent to Clay with null names.

**What was done:**
- Backfilled names from `core.company_customers` and `core.companies` (26 still null)
- The 851 rows already sent to Clay still have null names on Clay's side

**Root cause not diagnosed.** Two hypotheses:
1. Supabase `upsert()` with `on_conflict="case_study_url"` may not update non-conflict columns when matching pre-existing rows (from older pipeline migration)
2. `origin_company_name` was null in the original Clay webhook payloads

**Action Required:**
1. Check `raw.claygent_customers_structured_raw` — do the payloads for these domains contain `origin_company_name`?
2. Test Supabase upsert behavior with `on_conflict` — does it actually UPDATE all columns or just INSERT?
3. Add validation to `send_case_study_urls_to_clay` — skip/warn on null required fields before sending
4. Re-send the 851 rows to Clay with corrected names (reset `sent_to_clay = false` on those rows, re-trigger)

**Affected files:**
- `/modal-functions/src/ingest/company_customers_structured.py` (upsert to staging at line 115)
- `/modal-functions/src/ingest/send_case_study_urls.py` (no validation before sending)

**Docs:** `/docs/workflows/catalog/send-case-study-urls-to-clay.md`, `/docs/workflows/catalog/ingest-company-customers-structured.md`

---

### Modal Secret Misconfiguration (possibly stale)
**Status:** Unresolved (may no longer be relevant — `customers-of-2` / `v2` endpoint is deprecated)
**Date:** 2026-01-31

**Problem:** Modal function `ingest_company_customers_v2` is writing to a different Supabase project than expected. Webhook returns success but records don't appear in the database.

**Note:** `customers-of-2` was deprecated on 2026-02-04. Only `customers-of-3` (structured) is active. This issue may be moot.

**Affected Endpoint:** `modal-functions/src/ingest/company_customers_v2.py` (deprecated)

---

## Data Cleanup (Non-Urgent)

These items are non-urgent because affected records are already hidden from the dashboard via API filters.

### Companies: Delete records with no location data
- **Table:** `core.companies_missing_location`
- **Count:** ~55,000 companies
- **Criteria:** `discovery_location IS NULL AND salesnav_location IS NULL`
- **Why non-urgent:** API requires `company_country` - these leads don't show up anyway
- **SQL (run in small batches):**
```sql
DELETE FROM core.companies
WHERE id IN (
    SELECT id FROM core.companies_missing_location
    WHERE discovery_location IS NULL AND salesnav_location IS NULL
    LIMIT 100
);
```

### People: Backfill person_tenure with new start dates
- **Table:** `core.person_job_start_dates` has 4,858 people not in `core.person_tenure`
- **Action:** Insert these into person_tenure
- **Source:** Apollo InstantData "new in role" + SalesNav + person_profile start dates

### Reference Tables to Clean
| Table | Status | Notes |
|-------|--------|-------|
| `companies_missing_cleaned_name` | Can delete | Created for Clay enrichment |
| `people_missing_country` | Can delete | Created for backfill review |

---

## Funding Data Backfill

### Backfill core.company_funding from extracted.company_discovery
- **Source:** `extracted.company_discovery.total_funding_amount_range_usd`
- **Target:** `core.company_funding`
- **Delta:** ~96,000 companies with funding data not yet in core
- **Issue:** Direct INSERT with JOIN times out due to table size
- **Plan:** Create intermediate table first, then batch insert

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

## Person Enrichment Coalescing

### Create pipeline from extracted -> core tables
- **Issue:** Person enrichment workflow writes to `extracted` schema only, not `core`
- **Tables affected:**
  - `extracted.person_experience` -> should sync to `core.person_work_history`
  - `extracted.person_profile` -> should sync to `core.people`, `core.person_locations`, `core.person_job_titles`
- **Current state:** `core.person_work_history` has 1.25M rows but no automated sync from extracted
- **Action needed:** Create coalescing workflow (Modal function or scheduled job) that:
  1. Syncs new records from `extracted.person_experience` to `core.person_work_history`
  2. Applies job title mapping (`matched_job_function`, `matched_seniority`)
  3. Runs on schedule or triggered after enrichment completes
- **Why important:** Without this, newly enriched person data doesn't appear in past-employer queries

---

## Enrichment Workflow Visibility (Phased Plan)

### The Problem
We have **53 ingest functions** in Modal but only **16 registered workflows** in `reference.enrichment_workflow_registry`. This creates:
1. No visibility into which enrichments have run for a given entity
2. No tracking of what coalesces to `core` vs. what stops at `extracted`
3. No way for frontend to check "has this been enriched?"
4. Duplicate enrichment requests (wasted Clay credits)

### Phase 1: Complete the Registry (Foundation)
**Goal:** Every ingest function has a registered workflow with complete metadata.

**Schema changes to `reference.enrichment_workflow_registry`:**
```sql
ALTER TABLE reference.enrichment_workflow_registry ADD COLUMN IF NOT EXISTS
    raw_table text,
    extracted_table text,
    core_table text,
    key_column text,
    key_type text,
    coalesces_to_core boolean DEFAULT false,
    is_active boolean DEFAULT true;
```

**Action items:**
1. Audit all 53 Modal ingest functions
2. For each, identify: raw table, extracted table, whether it coalesces to core
3. Insert/update registry entries with complete metadata
4. Mark inactive workflows as `is_active = false`

### Phase 2: Enrichment Run Tracking
**Goal:** Track every enrichment execution at the entity level.

**New table:**
```sql
CREATE TABLE reference.enrichment_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name text NOT NULL REFERENCES reference.enrichment_workflow_registry(workflow_name),
    entity_key text NOT NULL,
    entity_type text NOT NULL,
    status text DEFAULT 'pending',
    records_processed int,
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    source text,
    UNIQUE(workflow_name, entity_key)
);
```

### Phase 3: Generic Status API Endpoint
**Goal:** Single endpoint to check enrichment status for any entity.

```
POST /api/enrichment/status
Body: { "entity_type": "company", "entity_key": "ironclad.com" }
```

### Phase 4: Coalescing Gap Detection
**Goal:** Automatically identify and fix extracted->core sync gaps.

### Phase 5: Enforcement & Automation
**Goal:** Make registration mandatory, coalescing automatic.

### Recommended Order
| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|--------------|
| 1. Complete Registry | Low | High | None |
| 2. Run Tracking | Medium | High | Phase 1 |
| 3. Status API | Low | Medium | Phase 1, 2 |
| 4. Gap Detection | Medium | High | Phase 1 |
| 5. Enforcement | High | High | All above |

**Start with Phase 1** - it's low effort but unlocks everything else.

---

## Completed Items

### Domain Cleanup (2026-01-31)
- [x] Updated `careersatdoordash.com` -> `doordash.com` across all schemas
- [x] Updated `aboutamazon.com` -> `amazon.com` across all schemas

---

## Notes

- **API required fields:** `company_name`, `company_country`, `person_country`, `matched_job_function`, `matched_seniority`
- Records missing any of these are automatically hidden from dashboard
- Focus enrichment efforts on filling these gaps to increase visible lead count
- **OpenAPI spec:** Regenerated 2026-01-31 (39 endpoints, all functional)
