# Star Schema Implementation Plan

## Overview

This document outlines the plan to implement a star schema for company and people data in the HQ data warehouse. The goal is to automate matching at ingest time, support multiple data sources with clear attribution, and eliminate manual backfill work.

---

## Problem Statement

### Current Pain Points

1. **Manual Backfills Required** - When new data arrives, we manually run pattern matching to populate `matched_job_function`, `matched_seniority`, `matched_industry`, etc.

2. **No Source Attribution** - Cannot tell which source (Clay, Crunchbase, Apollo) provided which data point

3. **Data Quality Varies by Source** - Clay normalizes "GE" to "Ge", Crunchbase names are better, but we can't prefer one over another

4. **Single-Source Tables** - Current tables assume one value per field per entity, can't store conflicting values from multiple sources

5. **Brittle Views** - `core.leads` and `core.companies_full` use LEFT JOINs that allow NULLs to slip through

---

## Target Architecture

### Star Schema Design

```
                    ┌─────────────────────┐
                    │  Coalesced Views    │
                    │  (Frontend/API)     │
                    │                     │
                    │  core.leads         │
                    │  core.companies_full│
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │ Dimension     │  │ Dimension     │  │ Dimension     │
    │ Tables        │  │ Tables        │  │ Tables        │
    │ (Company)     │  │ (People)      │  │ (Reference)   │
    └───────────────┘  └───────────────┘  └───────────────┘
            │                  │                  │
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │ Extraction    │  │ Extraction    │  │ Lookup        │
    │ Functions     │  │ Functions     │  │ Tables        │
    │ (Modal)       │  │ (Modal)       │  │               │
    └───────────────┘  └───────────────┘  └───────────────┘
            │                  │
            ▼                  ▼
    ┌─────────────────────────────────────┐
    │  Raw Payloads (raw.*)               │
    │  Clay, Apollo, SalesNav, etc.       │
    └─────────────────────────────────────┘
```

### Key Principles

1. **Composite Key**: `(entity_id, source)` - allows multiple sources per entity
2. **Raw + Matched**: Each dimension table stores both raw values and matched/normalized values
3. **Lookup at Ingest**: Extraction functions match against lookup tables when writing
4. **Coalesce with Priority**: Views combine sources with configurable priority (e.g., Crunchbase > Clay)

---

## Phase 1: Reference Tables (Foundation)

### 1.1 Create Missing Reference Tables

| Table | Purpose | Status |
|-------|---------|--------|
| `reference.company_types` | Public Company, Private Company, etc. | ✅ Created |
| `reference.funding_ranges` | <$1M, $1M-$5M, ..., $1B+ | ✅ Created |
| `reference.revenue_ranges` | <$1M, $1M-$5M, ..., $100B+ | ✅ Created |
| `reference.funding_range_lookup` | Maps Clay strings → our ranges | ✅ Created |
| `reference.revenue_range_lookup` | Maps Clay strings → our ranges | ✅ Created |

### 1.2 Audit Existing Reference Tables

| Table | Status | Notes |
|-------|--------|-------|
| `reference.employee_ranges` | ✅ Exists | 8 ranges, 1-10 through 10001+ |
| `reference.employee_range_lookup` | ✅ Exists | Maps Clay size strings |
| `reference.company_industries` | ✅ Exists | ~150 industries |
| `reference.industry_lookup` | ✅ Exists | Maps raw → matched |
| `reference.job_functions` | ✅ Exists | 12 functions + Executive Leadership |
| `reference.seniorities` | ✅ Exists | 10 levels + Individual Contributor |
| `reference.job_title_lookup` | ✅ Exists | Title → function/seniority mapping |

---

## Phase 2: Company Dimension Tables

### 2.1 Table Definitions

Each table follows this pattern:
- Primary key: `id` (UUID)
- Composite unique: `(domain, source)`
- Raw fields: exactly what source provided
- Matched fields: normalized values from lookups
- Timestamps: `created_at`, `updated_at`

| Table | Key Fields | Lookup Table |
|-------|------------|--------------|
| `core.company_names` | raw_name, cleaned_name, linkedin_url | Manual/Crunchbase |
| `core.company_employee_ranges` | raw_size, raw_employee_count, matched_employee_range | `reference.employee_range_lookup` |
| `core.company_types` | raw_type, matched_type | `reference.company_types` |
| `core.company_locations` | raw_location, raw_country, matched_city/state/country | `reference.company_location_lookup` |
| `core.company_industries` | raw_industry, raw_industries, matched_industry | `reference.industry_lookup` |
| `core.company_funding` | raw_funding_range, matched_funding_range | `reference.funding_range_lookup` |
| `core.company_revenue` | raw_revenue_range, matched_revenue_range | `reference.revenue_range_lookup` |
| `core.company_descriptions` | description, tagline | N/A |

### 2.2 Migration Strategy for Existing Tables

**Option A: Modify Existing Tables**
- Add `raw_*` columns to existing `core.company_*` tables
- Change unique constraint from `domain` to `(domain, source)`
- Backfill `source = 'legacy'` for existing data

**Option B: Create New Tables (Recommended)**
- Create new tables with `_v2` suffix or clean names
- Backfill from existing data + `extracted.company_discovery`
- Update views to use new tables
- Drop old tables after validation

### 2.3 Task List

- [ ] Decide on migration strategy (Option A vs B)
- [ ] Create/modify dimension tables
- [ ] Backfill from `extracted.company_discovery` (Clay source)
- [ ] Backfill from `extracted.company_firmographics` (LinkedIn source)
- [ ] Create `core.companies_full_v2` coalesced view
- [ ] Update API to use new view
- [ ] Validate data quality
- [ ] Remove old tables/views

---

## Phase 3: People Dimension Tables

### 3.1 Table Definitions

| Table | Key Fields | Lookup Table |
|-------|------------|--------------|
| `core.person_names` | raw_name, cleaned_name, linkedin_url | N/A |
| `core.person_job_titles` | raw_title, matched_cleaned_title, matched_job_function, matched_seniority | `reference.job_title_lookup` |
| `core.person_locations` | raw_location, matched_city/state/country | `reference.location_lookup` |
| `core.person_companies` | company_domain, job_start_date, is_current | N/A |

### 3.2 Current State

`core.person_job_titles` already exists with:
- `linkedin_url` (primary key)
- `raw_job_title`
- `matched_cleaned_job_title`
- `matched_job_function`
- `matched_seniority`

**Needed changes:**
- Add `source` column
- Change primary key to `(linkedin_url, source)`
- Or create new table with correct schema

### 3.3 Task List

- [ ] Audit existing `core.person_job_titles` schema
- [ ] Add source attribution
- [ ] Create person_locations dimension table
- [ ] Create `core.people_full_v2` coalesced view
- [ ] Update API to use new view

---

## Phase 4: Extraction Function Updates

### 4.1 Company Extraction (`modal-mcp-server/src/extraction/company.py`)

**Current functions:**
- `extract_company_firmographics()` - LinkedIn data → `extracted.company_firmographics`
- `extract_find_companies()` - Clay data → `extracted.company_discovery`
- `extract_find_companies_location_parsed()` - Clay data with parsed location

**Updates needed:**

```python
def extract_find_companies(supabase, raw_payload_id, company_domain, payload, clay_table_url=None):
    """
    Extract company data from Clay payload to dimension tables.
    Matches against lookup tables at ingest time.
    """
    source = "clay"

    # 1. Write to company_names
    write_company_name(supabase, domain, source, payload.get("name"), payload.get("linkedin_url"))

    # 2. Write to company_employee_ranges (with lookup)
    raw_size = payload.get("size")
    matched_range = lookup_employee_range(supabase, raw_size)
    write_company_employee_range(supabase, domain, source, raw_size, matched_range)

    # 3. Write to company_types (with lookup)
    raw_type = payload.get("type")
    matched_type = lookup_company_type(supabase, raw_type)
    write_company_type(supabase, domain, source, raw_type, matched_type)

    # 4. Write to company_locations (with lookup)
    raw_location = payload.get("location")
    raw_country = payload.get("country")
    parsed = lookup_location(supabase, raw_location, raw_country)
    write_company_location(supabase, domain, source, raw_location, raw_country, parsed)

    # 5. Write to company_industries (with lookup)
    raw_industry = payload.get("industry")
    matched_industry = lookup_industry(supabase, raw_industry)
    write_company_industry(supabase, domain, source, raw_industry, matched_industry)

    # 6. Write to company_funding (with lookup)
    raw_funding = payload.get("total_funding_amount_range_usd")
    matched_funding = lookup_funding_range(supabase, raw_funding)
    write_company_funding(supabase, domain, source, raw_funding, matched_funding)

    # 7. Write to company_revenue (with lookup)
    raw_revenue = payload.get("annual_revenue")
    matched_revenue = lookup_revenue_range(supabase, raw_revenue)
    write_company_revenue(supabase, domain, source, raw_revenue, matched_revenue)

    # 8. Write to company_descriptions
    write_company_description(supabase, domain, source, payload.get("description"))
```

### 4.2 People Extraction

Similar pattern for `extract_find_people()`:
- Match job title against `reference.job_title_lookup`
- Parse location against location lookup
- Write to dimension tables with source attribution

### 4.3 Task List

- [ ] Create helper functions for lookups
- [ ] Create helper functions for dimension table writes
- [ ] Update `extract_find_companies()` to use new pattern
- [ ] Update `extract_company_firmographics()` to use new pattern
- [ ] Update `extract_find_people()` to use new pattern
- [ ] Add unit tests for extraction functions
- [ ] Test with sample payloads

---

## Phase 5: Coalesced Views

### 5.1 Company View

```sql
CREATE OR REPLACE VIEW core.companies_full_v2 AS
SELECT
    domain,

    -- Name: prefer crunchbase > clay > apollo
    COALESCE(
        (SELECT cleaned_name FROM core.company_names WHERE domain = d.domain AND source = 'crunchbase'),
        (SELECT cleaned_name FROM core.company_names WHERE domain = d.domain AND source = 'clay'),
        (SELECT raw_name FROM core.company_names WHERE domain = d.domain AND source = 'clay')
    ) AS name,

    -- Employee range: any source
    (SELECT matched_employee_range FROM core.company_employee_ranges
     WHERE domain = d.domain AND matched_employee_range IS NOT NULL LIMIT 1) AS employee_range,

    -- Location: prefer source with most complete data
    ...

FROM (SELECT DISTINCT domain FROM core.company_names) d;
```

### 5.2 Leads View

Update `core.leads` to:
1. Use new dimension tables
2. Require all fields to be NOT NULL in WHERE clause (not just via API filters)
3. Join on domain/linkedin_url with priority logic

---

## Phase 6: Backfill Existing Data

### 6.1 Company Data Sources

| Source | Table | Records | Priority |
|--------|-------|---------|----------|
| Clay find-companies | `extracted.company_discovery` | ~50k | 2 |
| LinkedIn firmographics | `extracted.company_firmographics` | ~10k | 1 |
| Apollo | `extracted.apollo_companies` | TBD | 3 |
| Manual | Various | ~500 | 0 (highest) |

### 6.2 Backfill SQL Pattern

```sql
-- Backfill company_employee_ranges from extracted.company_discovery
INSERT INTO core.company_employee_ranges (domain, source, raw_size, matched_employee_range)
SELECT
    cd.domain,
    'clay' as source,
    cd.size as raw_size,
    erl.size_cleaned as matched_employee_range
FROM extracted.company_discovery cd
LEFT JOIN reference.employee_range_lookup erl ON cd.size = erl.size_raw
ON CONFLICT (domain, source) DO UPDATE SET
    raw_size = EXCLUDED.raw_size,
    matched_employee_range = EXCLUDED.matched_employee_range,
    updated_at = NOW();
```

### 6.3 Task List

- [ ] Backfill company_names from all sources
- [ ] Backfill company_employee_ranges
- [ ] Backfill company_types
- [ ] Backfill company_locations
- [ ] Backfill company_industries
- [ ] Backfill company_funding
- [ ] Backfill company_revenue
- [ ] Backfill company_descriptions
- [ ] Validate record counts match expectations
- [ ] Validate no data loss from old tables

---

## Phase 7: API Updates

### 7.1 Changes Required

1. Update `core()` helper to use new views
2. Update `COMPANY_COLUMNS` and `LEAD_COLUMNS` constants
3. Add new filter parameters for funding/revenue ranges
4. Update `/api/filters` endpoint to include new dropdowns

### 7.2 New Filter Endpoints

```python
@router.get("/funding-ranges", response_model=List[FilterOption])
async def get_funding_ranges():
    result = reference().from_("funding_ranges").select("name, sort_order").order("sort_order").execute()
    return [FilterOption(**row) for row in result.data]

@router.get("/revenue-ranges", response_model=List[FilterOption])
async def get_revenue_ranges():
    result = reference().from_("revenue_ranges").select("name, sort_order").order("sort_order").execute()
    return [FilterOption(**row) for row in result.data]
```

---

## Timeline Estimate

| Phase | Description | Dependency |
|-------|-------------|------------|
| 1 | Reference tables | None |
| 2 | Company dimension tables | Phase 1 |
| 3 | People dimension tables | Phase 1 |
| 4 | Extraction function updates | Phase 2, 3 |
| 5 | Coalesced views | Phase 2, 3 |
| 6 | Backfill existing data | Phase 2, 3, 5 |
| 7 | API updates | Phase 5, 6 |

---

## Success Criteria

1. **No manual backfills** - New data automatically matched at ingest
2. **Source attribution** - Can query which source provided each data point
3. **Data quality** - Can prefer Crunchbase names over Clay names
4. **Complete leads** - All visible leads have all required fields
5. **No regressions** - Lead count >= current 863k
6. **API performance** - Response times unchanged or improved

---

## Open Questions

1. **Existing table migration**: Modify in place or create new tables?
2. **Historical data**: Keep old `extracted.*` tables or migrate all to dimension tables?
3. **Source priority**: What's the exact priority order for each field?
4. **Crunchbase integration**: When/how will Crunchbase data be ingested?
5. **Apollo integration**: Current state of Apollo data pipeline?

---

## Appendix: Example Clay Payload

```json
{
  "name": "Google",
  "size": "10,001+ employees",
  "type": "Public Company",
  "domain": "google.com",
  "country": "United States",
  "industry": "Software Development",
  "location": "Mountain View, CA",
  "industries": ["Software Development"],
  "description": "A multinational technology company...",
  "linkedin_url": "https://www.linkedin.com/company/google",
  "annual_revenue": "100B-1T",
  "clay_company_id": 47884714,
  "resolved_domain": {...},
  "linkedin_company_id": 1441,
  "total_funding_amount_range_usd": "$100M - $250M"
}
```

Maps to dimension tables:
- `company_names`: name="Google", linkedin_url="..."
- `company_employee_ranges`: raw_size="10,001+ employees", matched="10001+"
- `company_types`: raw_type="Public Company", matched="Public Company"
- `company_locations`: raw_location="Mountain View, CA", matched_city="Mountain View", matched_state="California", matched_country="United States"
- `company_industries`: raw_industry="Software Development", matched="Software Development"
- `company_funding`: raw="$100M - $250M", matched="$100M - $250M"
- `company_revenue`: raw="100B-1T", matched="$100B+"
