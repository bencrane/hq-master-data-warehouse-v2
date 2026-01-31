# Data Warehouse Update - January 28, 2026

## Architecture Understanding

### System Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Modal (hq-master-data-ingest)** | Ingest webhooks from Clay, write to raw/extracted tables | `modal-mcp-server/` |
| **HQ API** | Query API for frontend dashboard | `hq-api/` |
| **Supabase** | PostgreSQL database with raw/extracted/core/reference schemas | Cloud |
| **Frontend** | Dashboard consuming HQ API | `frontend/` |

### Data Flow

```
Clay Table → Modal Webhook → raw.* table → extracted.* table
                                              ↓
                              (consolidation/backfill SQL)
                                              ↓
                                         core.* table
                                              ↓
                                     HQ API endpoint
                                              ↓
                                         Frontend
```

### Schema Purposes

| Schema | Purpose | Example |
|--------|---------|---------|
| `raw` | Unprocessed webhook payloads | `raw.claygent_customers_v2_raw` |
| `extracted` | Parsed/flattened records from raw | `extracted.claygent_customers_v2` |
| `core` | Consolidated, canonical data for API | `core.company_customers` |
| `reference` | Lookup tables for normalization | `reference.job_functions` |
| `public` | Utility tables, NOT for frontend | `public.top_priority_companies` |

### What Frontend Queries (via HQ API)

Only `core` schema views/tables:
- `core.leads` - main leads view
- `core.companies_full` - company data
- `core.leads_recently_promoted` - promotion signal
- `core.leads_at_vc_portfolio` - VC portfolio signal
- `core.company_customers` - used by `/api/leads/by-company-customers`

### What Frontend Does NOT Query

- `raw.*` - internal storage
- `extracted.*` - intermediate processing
- `public.top_priority_companies` - workflow helper for prioritizing which companies to enrich next
- `staging.*` - temporary processing tables

---

## Work Completed Today (2026-01-28)

### 1. Company Enrich Similar Companies - Async Refactor

**Problem:** Batch of 598 domains caused frontend timeout; Modal function also timed out at 89/598.

**Solution:** Refactored to async architecture:
- `find_similar_companies_batch` - creates batch, spawns worker, returns immediately with batch_id
- `process_similar_companies_batch` - background worker via `.spawn()`, 4-hour timeout
- `get_similar_companies_batch_status` - polling endpoint for progress

**Tables:**
- `raw.company_enrich_similar_batches` - batch tracking (status, progress, error_message)
- `raw.company_enrich_similar_raw` - API responses per domain
- `extracted.company_enrich_similar` - parsed similar companies

**Current batch:** `ec77a3a3-4e98-4c6c-8227-7b3c7ae36453` (598 domains, status unknown)

### 2. Claygent Customer Ingest Endpoints

Created 3 Modal endpoints for different Clay payload formats:

| Endpoint | Payload Format | Raw Table | Extracted Table |
|----------|----------------|-----------|-----------------|
| `ingest_company_customers_claygent` | Comma-separated string result | `raw.claygent_customers_raw` | `extracted.claygent_customers` |
| `ingest_company_customers_structured` | Array of {url, companyName, hasCaseStudy} | `raw.claygent_customers_structured_raw` | `extracted.claygent_customers_structured` |
| `ingest_company_customers_v2` | Same as structured, handles empty arrays | `raw.claygent_customers_v2_raw` | `extracted.claygent_customers_v2` |

**Purpose:** These are INGEST endpoints only. Data flows to `extracted.*` tables, NOT directly to API.

### 3. Customer Name Matching

Added columns to extracted tables for matching customer names to known companies:
- `matched_domain` - domain from `core.companies` or `extracted.company_discovery`
- `matched_linkedin_url` - linkedin URL from same sources

Match rate: ~48% of customer names matched to domains.

### 4. Top Priority Companies Table

**Table:** `public.top_priority_companies`
- Purpose: Manual upload of companies to prioritize for enrichment workflows
- Fields: `company_name`, `domain`, `company_linkedin_url`
- Records: 7,367 companies, 6,318 with linkedin URLs populated
- NOT an API table - used internally to drive Clay table inputs

---

## Pending Work

### 1. Consolidate Claygent Customers into core.company_customers

The 3 `extracted.claygent_*` tables need to be consolidated into `core.company_customers` for the existing API endpoint to serve them.

**SQL needed:**
```sql
INSERT INTO core.company_customers (
    origin_company_domain,
    origin_company_name,
    customer_name,
    customer_domain,
    case_study_url,
    has_case_study,
    source
)
SELECT DISTINCT
    origin_company_domain,
    origin_company_name,
    customer_name,
    matched_domain,
    case_study_url,
    has_case_study,
    'claygent_v2'
FROM extracted.claygent_customers_v2
WHERE matched_domain IS NOT NULL
ON CONFLICT DO NOTHING;

-- Repeat for claygent_customers and claygent_customers_structured
```

### 2. Check Similar Companies Batch Status

Query `raw.company_enrich_similar_batches` for batch `ec77a3a3-4e98-4c6c-8227-7b3c7ae36453`.

### 3. Backfill Work (from earlier session)

Completed:
- Person job titles backfill (+219k)
- Person locations backfill (+217k)

Deprioritized:
- Company types - can filter at API level instead

---

## API Endpoint Summary

### Existing HQ API Endpoints (in `hq-api/routers/`)

| Endpoint | Source Table/View | Purpose |
|----------|-------------------|---------|
| `GET /api/leads` | `core.leads` | Main leads query |
| `GET /api/leads/new-in-role` | `core.leads` | New hires signal |
| `GET /api/leads/recently-promoted` | `core.leads_recently_promoted` | Promotion signal |
| `GET /api/leads/at-vc-portfolio` | `core.leads_at_vc_portfolio` | VC portfolio signal |
| `GET /api/leads/by-past-employer` | `core.get_leads_by_past_employer()` | Past employer filter |
| `GET /api/leads/by-company-customers` | `core.get_leads_by_company_customers()` | Customer alumni filter |
| `GET /api/companies` | `core.companies_full` | Company search |
| `GET /api/filters/*` | `reference.*` | Filter dropdowns |

### Modal Ingest Endpoints (in `modal-mcp-server/src/ingest/`)

These receive webhooks and write to raw/extracted - they are NOT query APIs:
- `ingest_company_customers_claygent`
- `ingest_company_customers_structured`
- `ingest_company_customers_v2`
- `find_similar_companies_batch`
- `find_similar_companies_single`
- `get_similar_companies_batch_status`
- (plus ~40 other ingest endpoints)

---

## Key Understanding

1. **Modal endpoints are for INGEST** - they receive data and write to database
2. **HQ API endpoints are for QUERY** - they read from `core` schema for frontend
3. **`public.top_priority_companies` is a workflow table** - not for frontend, used to drive which companies get enriched
4. **Data must flow through consolidation** - `extracted.*` → `core.*` before it appears in API
5. **The existing `/api/leads/by-company-customers` endpoint works** - it queries `core.company_customers`, which was populated on 2026-01-26 with initial data
