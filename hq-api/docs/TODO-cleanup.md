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

## Person Enrichment Coalescing

### Create pipeline from extracted → core tables
- **Issue:** Person enrichment workflow writes to `extracted` schema only, not `core`
- **Tables affected:**
  - `extracted.person_experience` → should sync to `core.person_work_history`
  - `extracted.person_profile` → should sync to `core.people`, `core.person_locations`, `core.person_job_titles`
- **Current state:** `core.person_work_history` has 1.25M rows but no automated sync from extracted
- **Action needed:** Create coalescing workflow (Modal function or scheduled job) that:
  1. Syncs new records from `extracted.person_experience` to `core.person_work_history`
  2. Applies job title mapping (`matched_job_function`, `matched_seniority`)
  3. Runs on schedule or triggered after enrichment completes
- **Why important:** Without this, newly enriched person data doesn't appear in past-employer queries

---

## Enrichment Workflow Visibility - Phased Plan

### The Problem

We have **53 ingest functions** in Modal but only **16 registered workflows** in `reference.enrichment_workflow_registry`. This creates:
1. No visibility into which enrichments have run for a given entity (company/person)
2. No tracking of what coalesces to `core` vs. what stops at `extracted`
3. No way for frontend to check "has this been enriched?"
4. Duplicate enrichment requests (wasted Clay credits)

### Root Cause

The issue is **registration discipline** - workflows were added ad-hoc without consistent metadata tracking. The registry exists but isn't enforced or complete.

---

### Phase 1: Complete the Registry (Foundation)

**Goal:** Every ingest function has a registered workflow with complete metadata.

**Schema changes to `reference.enrichment_workflow_registry`:**
```sql
ALTER TABLE reference.enrichment_workflow_registry ADD COLUMN IF NOT EXISTS
    raw_table text,
    extracted_table text,
    core_table text,  -- NULL if doesn't coalesce
    key_column text,  -- 'domain', 'linkedin_url', etc.
    key_type text,    -- 'company', 'person'
    coalesces_to_core boolean DEFAULT false,
    is_active boolean DEFAULT true;
```

**Action items:**
1. Audit all 53 Modal ingest functions
2. For each, identify: raw table, extracted table, whether it coalesces to core
3. Insert/update registry entries with complete metadata
4. Mark inactive workflows as `is_active = false`

**Deliverable:** Complete registry showing all workflows and their data flow.

---

### Phase 2: Enrichment Run Tracking

**Goal:** Track every enrichment execution at the entity level.

**New table:**
```sql
CREATE TABLE reference.enrichment_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_name text NOT NULL REFERENCES reference.enrichment_workflow_registry(workflow_name),
    entity_key text NOT NULL,        -- domain or linkedin_url
    entity_type text NOT NULL,       -- 'company' or 'person'
    status text DEFAULT 'pending',   -- pending, running, completed, failed
    records_processed int,
    started_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    source text,                     -- 'clay', 'apollo', 'manual', etc.
    UNIQUE(workflow_name, entity_key)
);

CREATE INDEX idx_enrichment_runs_entity ON reference.enrichment_runs(entity_type, entity_key);
CREATE INDEX idx_enrichment_runs_workflow ON reference.enrichment_runs(workflow_name, status);
```

**Action items:**
1. Modify ingest functions to insert/update `enrichment_runs` on completion
2. Backfill from existing `extracted` tables where possible (use `created_at`)
3. Add constraint: ingest functions must log to registry

---

### Phase 3: Generic Status API Endpoint

**Goal:** Single endpoint to check enrichment status for any entity.

**Recommended approach:** YES, build the generic endpoint. Here's why:
- Avoids N separate endpoints for N enrichment types
- Frontend can check all enrichments in one call
- Enables "enrichment coverage" dashboard

**API Design Convention:** Use POST with request body for all query endpoints (not GET with query params).
- Cleaner URLs, no encoding issues with special characters (e.g., LinkedIn URLs)
- Consistent with existing `/work-history`, `/enrichment-status` endpoints
- Request body is more structured and readable

**Endpoint design:**
```
POST /api/enrichment/status
Body: { "entity_type": "company", "entity_key": "ironclad.com" }

POST /api/enrichment/status
Body: { "entity_type": "person", "entity_key": "linkedin.com/in/johndoe" }
```

**Response:**
```json
{
  "entity_type": "company",
  "entity_key": "ironclad.com",
  "enrichments": [
    {
      "workflow_name": "company_discovery",
      "status": "completed",
      "completed_at": "2024-01-15T10:30:00Z",
      "coalesces_to_core": true,
      "records_in_extracted": 1,
      "records_in_core": 1
    },
    {
      "workflow_name": "company_customers",
      "status": "completed",
      "completed_at": "2024-01-20T14:00:00Z",
      "coalesces_to_core": false,  -- Gap identified!
      "records_in_extracted": 25,
      "records_in_core": 0
    },
    {
      "workflow_name": "company_funding",
      "status": "not_run",
      "coalesces_to_core": true
    }
  ],
  "coverage": {
    "total_workflows": 8,
    "completed": 5,
    "pending": 1,
    "not_run": 2
  }
}
```

---

### Phase 4: Coalescing Gap Detection

**Goal:** Automatically identify and fix extracted→core sync gaps.

**View for gap detection:**
```sql
CREATE VIEW reference.coalescing_gaps AS
SELECT
    r.workflow_name,
    r.extracted_table,
    r.core_table,
    COUNT(DISTINCT e.key) as in_extracted,
    COUNT(DISTINCT c.key) as in_core,
    COUNT(DISTINCT e.key) - COUNT(DISTINCT c.key) as gap
FROM reference.enrichment_workflow_registry r
-- Dynamic query per workflow would go here
WHERE r.coalesces_to_core = true
  AND r.core_table IS NOT NULL;
```

**Action items:**
1. Build scheduled job to check for gaps
2. Alert when gap exceeds threshold
3. Create coalescing functions for each workflow type

---

### Phase 5: Enforcement & Automation

**Goal:** Make registration mandatory, coalescing automatic.

1. **Pre-commit hook or CI check:** New ingest functions must have registry entry
2. **Automated coalescing:** After ingest completes, trigger core sync if `coalesces_to_core = true`
3. **Dashboard:** Show enrichment coverage by workflow, gaps, and trends

---

### Recommended Order of Execution

| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|--------------|
| 1. Complete Registry | Low | High | None |
| 2. Run Tracking | Medium | High | Phase 1 |
| 3. Status API | Low | Medium | Phase 1, 2 |
| 4. Gap Detection | Medium | High | Phase 1 |
| 5. Enforcement | High | High | All above |

**Start with Phase 1** - it's low effort but unlocks everything else. Without a complete registry, the other phases can't work.

---

### Answer to Your Question

**Is the generic status endpoint the right approach?**

Yes, but it's Phase 3, not Phase 1. The endpoint only works if:
1. Registry is complete (knows all workflows)
2. Run tracking exists (knows what's been executed)

Building the endpoint first without the foundation would require hardcoded logic for each enrichment type, which defeats the purpose.

**The real fix is registration discipline (Phase 1)** - once every workflow is registered with its metadata, the status endpoint becomes a simple query against the registry + run tracking tables.

---

## Notes

- API required fields: `company_name`, `company_country`, `person_country`, `matched_job_function`, `matched_seniority`
- Records missing any of these are automatically hidden from dashboard
- Focus enrichment efforts on filling these gaps to increase visible lead count
