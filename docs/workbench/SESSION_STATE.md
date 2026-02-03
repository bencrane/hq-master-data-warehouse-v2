# Session State

**Last updated:** 2026-02-03

This file tracks the current state of work. Update after every major milestone.

---

## Just Completed (Phase 2: Client Lead Ingest & Person Profile Enhancement)

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
│  raw.* → extracted.* → reference.* → core.* + client.*          │
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

- Testing person profile ingest with new core table writes

---

## Blocked / Waiting

- None

---

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `/hq-api/routers/run.py` | Added client lead, job-title/location update endpoints |
| `/modal-functions/src/ingest/person.py` | Extended to populate core tables |
| `/modal-functions/src/extraction/person_core.py` | NEW - Core table extraction functions |

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

---

## Database Connection

```
postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```
