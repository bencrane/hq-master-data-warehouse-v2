# Session State

**Last updated:** 2026-02-04

This file tracks the current state of work. Update after every major milestone.

---

## Just Completed (2026-02-04: CompanyEnrich Workflow with Core Coalescing)

### CompanyEnrich.com Workflow (Complete + Core Coalescing)
Full company enrichment workflow: raw → extracted breakout tables → core tables. Single endpoint populates the entire company profile.

**Endpoints:**
- **Modal:** `https://bencrane--hq-master-data-ingest-ingest-companyenrich.modal.run`
- **API:** `POST /run/companies/companyenrich/ingest`

**Extracted Tables (13):** raw payload + main company table + 11 breakout tables

**Core Tables Coalesced (16):**

| Core Table | Data | Behavior |
|------------|------|----------|
| `core.companies` | name, domain, linkedin_url | Insert if not exists |
| `core.company_names` | raw_name, linkedin_url | Insert if not exists, never overwrite cleaned_name |
| `core.company_employee_range` | matched via reference lookup | Upsert |
| `core.company_revenue` | matched via reference lookup (upper-end) | Upsert on domain+source |
| `core.company_types` | private→Private Company, etc. | Upsert on domain+source |
| `core.company_locations` | pre-parsed city/state/country | Only overwrite if more data |
| `core.company_descriptions` | description + seo_description as tagline | Upsert |
| `core.company_industries` | industry + reference insert | Insert if not exists |
| `core.company_tech_on_site` | via reference.technologies | Upsert per tech |
| `core.company_keywords` | each keyword | Upsert per keyword |
| `core.company_categories` | each category | Upsert per category |
| `core.company_naics_codes` | each NAICS code | Upsert per code |
| `core.company_funding_rounds` | each funding round | Upsert per round |
| `core.company_vc_investors` | parsed from funding `from` field | Upsert per investor |
| `core.company_vc_backed` | vc_count = distinct investors | Upsert |
| `core.company_social_urls` | all social URLs | Upsert |

**New Core Tables Created:** `core.company_funding_rounds`, `core.company_categories`, `core.company_keywords`, `core.company_naics_codes`

**Renamed Tables:** `core.company_technologies` → `core.company_tech_on_site`, `core.company_linkedin_urls` → `core.company_social_urls`

**New Reference Lookups Added:**
- `reference.employee_range_lookup`: companyenrich values (501-1K, 1K-5K, 5K-10K, over-10K)
- `reference.revenue_range_lookup`: companyenrich values (1m-10m, 10m-50m, etc.) mapped to upper-end canonical

**Documentation:** `/docs/workflows/catalog/ingest-companyenrich.md`

**Tested end-to-end:** pactos.ai (new company, all 16 core tables populated), antimetal.com (existing company, conditional logic verified)

### SalesNav Export to Clay Webhook Endpoint
Created endpoint to send SalesNav export files directly to Clay webhooks:
- **Endpoint:** `POST /run/salesnav/export/to-clay`
- **Features:**
  - Accepts TSV/CSV file upload + Clay webhook URL
  - Auto-detects delimiter (TSV vs CSV)
  - Sends rows to Clay in background at 10 records/second
  - Returns immediately with row count (fire-and-forget)
- **Form fields:** `file`, `webhook_url`, `export_title`, `export_timestamp`, `notes`

### CORS Updates
- Added localhost ports 3000-3015 to allowed origins for development

### Testing Schema & Endpoint
- **New schema:** `testing`
- **New table:** `testing.companies` (id, name, domain, linkedin_url, created_at)
- **New endpoint:** `POST /run/testing/companies` - Insert company into testing table

---

## Previously Completed (Phase 2: Client Lead Ingest & Person Profile Enhancement)

### Generic Database Read/Check Endpoint
Created a safe, generic endpoint to check if a domain exists in any table:
- **API Endpoint:** `POST /read/companies/db/check-existence`
- **Modal Function:** `read_db_check_existence`
- **Features:** 
  - Validates schema/table names (alphanumeric only)
  - Uses parameterized queries for safety
  - Returns boolean `exists` flag

### Client Lead Ingest System
Created client schema and lead tracking for multi-tenant support:

- **New schema:** `client.*`
- **New tables:**
  - `client.leads` - denormalized lead data with all fields
  - `client.leads_people` - normalized person data
  - `client.leads_companies` - normalized company data
- **New endpoint:** `POST /run/client/leads/ingest`
- **Fields tracked:** client_domain, client_form_id, client_form_title, person info, company info

### Reference Table Lookup/Update Endpoints
Created modular lookup pattern for Clay orchestration:

**Lookup endpoints (check if exists):**
- `POST /run/people/db/person-job-title/lookup` - returns cleaned_job_title, seniority_level, job_function
- `POST /run/people/db/person-location/lookup` - returns city, state, country

**Update endpoints (add new entries):**
- `POST /run/reference/job-title/update` - add to reference.job_title_lookup
- `POST /run/reference/location/update` - add to reference.location_lookup

### Person Profile Ingest Extended to Core Tables
Enhanced `ingest_clay_person_profile` Modal function to populate:

| Core Table | Action | Data Source |
|------------|--------|-------------|
| `core.people` | check/insert | linkedin_url, full_name, slug |
| `core.companies` | check/insert per company | experience array (deduped by domain) |
| `core.person_locations` | upsert | location_name, country |
| `core.person_tenure` | upsert | latest job start_date |
| `core.person_past_employer` | delete+insert | experiences where is_current=false |

**New file:** `/modal-functions/src/extraction/person_core.py`

### Public Company Ticker Backfill
- Added `ticker` column to `core.company_public`
- Created `POST /run/companies/db/public-ticker/backfill` endpoint
- For SEC CIK lookups via Clay

### Job Title Lookup Table Backfill
Backfilled `reference.job_title_lookup` with job_function and seniority from extracted tables:
- 13,774 rows updated with job_function
- 12,908 rows updated with seniority_level

---

## Enrichment Protocol (Decision Made)

**Pattern for lookups from Clay:**
1. Clay calls lookup API (e.g., `/run/people/db/person-job-title/lookup`)
2. If `match_status: true` → use returned values
3. If `match_status: false` → run enrichment (Gemini, etc.)
4. Call update endpoint to add to lookup table (e.g., `/run/reference/job-title/update`)
5. Proceed with enriched data

**Design decision:** DB does lookups during ingest (not optimized yet). Clay ensures lookup table has entries before sending. Optimization deferred.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     api.revenueinfra.com                         │
├─────────────────────────────────────────────────────────────────┤
│  /api/leads/*          │  Existing leads API                    │
│  /api/companies/*      │  Company lookup/enrichment             │
│  /api/people/*         │  People work history/enrichment        │
│  /api/enrichment/*     │  Workflow registry & status            │
│  /run/*                │  Modal function wrappers (80+)         │
│  /run/client/*         │  Client lead ingest                    │
│  /run/reference/*      │  Reference table updates               │
│  /run/salesnav/*       │  SalesNav export to Clay               │
│  /run/testing/*        │  Testing/dev endpoints                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              Modal Serverless Functions                          │
│  https://bencrane--hq-master-data-ingest-{function}.modal.run   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase PostgreSQL                           │
│  raw.* → extracted.* → reference.* → core.* + client.* + testing.* │
└─────────────────────────────────────────────────────────────────┘
```

---

## Person Profile Ingest Flow

```
Clay sends: { linkedin_url, workflow_slug, raw_payload }
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ingest_clay_person_profile                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Store raw payload → raw.person_payloads                     │
│  2. Extract profile → extracted.person_profile (upsert)         │
│  3. Extract experience → extracted.person_experience (del+ins)  │
│     └─ Trigger: sync_person_experience_to_core()                │
│        └─ Populates: core.person_work_history                   │
│  4. Extract education → extracted.person_education (del+ins)    │
│  5. Upsert → core.people                                        │
│  6. Upsert companies → core.companies (from experience)         │
│  7. Upsert → core.person_locations                              │
│  8. Upsert → core.person_tenure                                 │
│  9. Insert → core.person_past_employer                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Currently In Progress

- None

---

## Blocked / Waiting

- None

---

## Key Files Modified This Session (2026-02-04)

| File | Changes |
|------|---------|
| `/hq-api/routers/run.py` | Added `/run/salesnav/export/to-clay`, `/run/testing/companies`, `/run/companies/companyenrich/ingest` |
| `/hq-api/main.py` | Added localhost ports 3000-3015 to CORS allowed origins |
| `/modal-functions/src/ingest/companyenrich.py` | NEW - CompanyEnrich.com ingestion with breakout tables + core coalescing (16 core tables) |
| `/modal-functions/src/app.py` | Added companyenrich import |
| `/docs/workflows/catalog/ingest-companyenrich.md` | NEW - Full workflow documentation |

## Schema Changes This Session

| Change | Details |
|--------|---------|
| Renamed `core.company_technologies` → `core.company_tech_on_site` | Removed first_detected/last_detected, added source |
| Renamed `core.company_linkedin_urls` → `core.company_social_urls` | Added twitter, facebook, github, youtube, instagram, crunchbase, g2, angellist columns |
| Created `core.tech_on_site_detections` | domain, technology_id (FK), first_detected, last_detected, source |
| Created `core.company_funding_rounds` | domain, source, funding_date, funding_type, amount, investors, url |
| Created `core.company_categories` | domain, category, source |
| Created `core.company_keywords` | domain, keyword, source |
| Created `core.company_naics_codes` | domain, naics_code, source |

## Key Files Modified Previous Session

| File | Changes |
|------|---------|
| `/hq-api/routers/run.py` | Added client lead, job-title/location update endpoints |
| `/modal-functions/src/ingest/person.py` | Extended to populate core tables |
| `/modal-functions/src/extraction/person_core.py` | NEW - Core table extraction functions |
| `/hq-api/routers/read.py` | NEW - Generic read router |
| `/modal-functions/src/read/db_check.py` | NEW - Safe DB check function |

---

## Key Tables Reference

### Lookup Tables
| Table | Key | Returns |
|-------|-----|---------|
| `reference.job_title_lookup` | latest_title | cleaned_job_title, seniority_level, job_function |
| `reference.location_lookup` | location_name | city, state, country, has_* |

### Core Person Tables
| Table | Purpose | Key |
|-------|---------|-----|
| `core.people` | Canonical person record | linkedin_url |
| `core.person_work_history` | All jobs (via trigger) | linkedin_url |
| `core.person_locations` | Person's location | linkedin_url |
| `core.person_tenure` | Current job start date | linkedin_url |
| `core.person_past_employer` | Previous companies | linkedin_url |
| `core.person_job_titles` | Matched title info | linkedin_url |

---

## API Quick Reference

### Client lead ingest
```bash
curl -X POST https://api.revenueinfra.com/run/client/leads/ingest \
  -H "Content-Type: application/json" \
  -d '{"client_domain":"acme.com","client_form_id":"form1","first_name":"John"}'
```

### Job title lookup
```bash
curl -X POST https://api.revenueinfra.com/run/people/db/person-job-title/lookup \
  -H "Content-Type: application/json" \
  -d '{"job_title":"Senior Sales Engineer"}'
```

### Add to job title lookup
```bash
curl -X POST https://api.revenueinfra.com/run/reference/job-title/update \
  -H "Content-Type: application/json" \
  -d '{"latest_title":"Senior Sales Engineer","cleaned_job_title":"Sales Engineer","seniority_level":"Senior","job_function":"Sales Engineering"}'
```

### SalesNav export to Clay (multipart form)
```bash
curl -X POST https://api.revenueinfra.com/run/salesnav/export/to-clay \
  -F "file=@export.csv" \
  -F "webhook_url=https://api.clay.com/v3/sources/webhook/..." \
  -F "export_title=Q1 2026 Leads" \
  -F "export_timestamp=1/25/2026, 10:15 PM"
```

### Add company to testing table
```bash
curl -X POST https://api.revenueinfra.com/run/testing/companies \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme Inc","domain":"acme.com","linkedin_url":"https://linkedin.com/company/acme"}'
```

---

## Database Connection

```
postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```
