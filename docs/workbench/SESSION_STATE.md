# Session State

**Last updated:** 2026-02-04

This file tracks the current state of work. Update after every major milestone.

---

## Just Completed (2026-02-04: Case Study URL Pipeline + Customer Data Cleanup)

### Case Study URL Pipeline (Clay → Gemini extraction)

Built end-to-end pipeline for sending case study URLs to Clay for Gemini extraction:

1. **Ingest customers** → `ingest_company_customers_structured` now pushes case study URLs to `raw.staging_case_study_urls`
2. **Send to Clay** → `send_case_study_urls_to_clay` Modal function sends staged URLs to Clay webhook at 10/sec
3. **Check if extracted** → `lookup_case_study_details` checks `extracted.case_study_details` by `case_study_url`

**Endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `POST /run/companies/claygent/customers-of-3/ingest` | Canonical "get customers of" ingest (writes to raw, extracted, core, staging) |
| `POST /run/case-study-urls/to-clay` | Send staged URLs to Clay webhook (Modal function, 10/sec) |
| `POST /run/companies/case-study-details/lookup` | Check if a case_study_url has been extracted |

**Table: `raw.staging_case_study_urls`**

| Column | Description |
|--------|-------------|
| origin_company_name | Company that published the case study |
| origin_company_domain | Publisher's domain (normalized bare) |
| customer_company_name | Featured customer |
| case_study_url | URL (unique constraint) |
| processed | Gemini extraction done and results ingested back |
| sent_to_clay | Fired to Clay webhook |
| batch_id | Optional batch filter |

Key distinction: `sent_to_clay` and `processed` are independent flags.

### Domain Normalization

Added `normalize_domain()` to `company_customers_structured.py`. Strips `https://`, `www.`, paths, trailing slashes, lowercases.

Cleaned up existing dirty data:
- `core.company_customers`: 7,336 duplicates deleted, 3,646 updated (10,982 total dirty rows)
- `raw.staging_case_study_urls`: 1,861 updated

### Customer Ingest Endpoint Consolidation

Deprecated `customers-of-1`, `customers-of-2`, `customers-of-4`. Only `customers-of-3` (structured) is active.

### Customer Data Backfills
- 200 rows from `extracted.claygent_customers` → `core.company_customers`
- 845 rows from `extracted.claygent_customers_structured` → `core.company_customers`
- 4,609 rows from `extracted.case_study_buyers` → `core.case_study_champions`

### Industry Normalization
Added `reference.industry_lookup` check to `companyenrich.py`. "Software" raw → "Software Development" canonical.

### Fixed Stale Table/Column Names
- `lookup_company_customers.py`: `company_employee_ranges` → `company_employee_range`, `industry` → `matched_industry`
- `db_check.py`: Added optional `column_name` parameter

---

## Open Issues / Bugs

### CRITICAL: origin_company_name null in staging table
**Status:** Not fully resolved
**Date:** 2026-02-04

1,040 rows in `raw.staging_case_study_urls` had `origin_company_name = NULL`. 851 of these were sent to Clay with null names. Backfilled from `core.company_customers` and `core.companies` (26 still null).

**Root cause not diagnosed.** The ingest code sets `origin_company_name` in the upsert payload. Possible causes:
- Supabase upsert with `on_conflict="case_study_url"` may not update all columns when matching pre-existing rows
- The `origin_company_name` field may not have been in the Clay webhook payload

**Action needed:**
1. Check `raw.claygent_customers_structured_raw` to confirm whether `origin_company_name` was in the original payloads
2. Test Supabase upsert behavior — does `on_conflict` actually update non-conflict columns?
3. Add validation to `send_case_study_urls_to_clay` to skip/warn on null required fields
4. Consider re-sending the 851 rows to Clay with correct names

### Railway background tasks die after HTTP response
**Status:** Resolved (moved to Modal)
Railway `asyncio.create_task()` dies when the HTTP response completes. Only 509/1039 rows sent. Solution: moved webhook sending to Modal function with 10min timeout.

### PostgREST `staging` schema not accessible
**Status:** Resolved (moved table to `raw` schema)
Despite `staging` appearing in Supabase dashboard config, PostgREST returns `PGRST106: The schema must be one of the following: public, raw, extracted, reference, core, manual, mapped`. Moved `staging.case_study_urls_to_process` → `raw.staging_case_study_urls`. Needed `GRANT ALL` to `service_role`.

---

## Previously Completed (CompanyEnrich Workflow with Core Coalescing)

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

**Documentation:** `/docs/workflows/catalog/ingest-companyenrich.md`

---

## Key Files Modified This Session (2026-02-04)

| File | Changes |
|------|---------|
| `/modal-functions/src/ingest/company_customers_structured.py` | Added `normalize_domain()`, added staging push to `raw.staging_case_study_urls` |
| `/modal-functions/src/ingest/send_case_study_urls.py` | NEW — Modal function to send staged URLs to Clay webhook |
| `/modal-functions/src/ingest/lookup_case_study_details.py` | NEW — Check if case_study_url exists in extracted.case_study_details |
| `/modal-functions/src/ingest/lookup_company_customers.py` | Fixed stale table/column names |
| `/modal-functions/src/ingest/companyenrich.py` | Added industry normalization via reference.industry_lookup |
| `/modal-functions/src/read/db_check.py` | Added optional column_name parameter |
| `/modal-functions/src/app.py` | Added imports for send_case_study_urls_to_clay, lookup_case_study_details |
| `/hq-api/routers/run.py` | Added API wrappers for case-study-urls/to-clay and case-study-details/lookup. Deprecated customers-of-1,2,4. Replaced Railway background task with Modal proxy. |
| `/docs/workflows/catalog/ingest-company-customers-structured.md` | Updated with staging push, domain normalization, known issues |
| `/docs/workflows/catalog/send-case-study-urls-to-clay.md` | NEW |
| `/docs/workflows/catalog/lookup-case-study-details.md` | NEW |
| `/docs/workflows/catalog/ingest-case-study-buyers.md` | Updated with core table section |

## Database Changes This Session

| Change | Details |
|--------|---------|
| Created `raw.staging_case_study_urls` | Moved from `staging.case_study_urls_to_process` |
| Added `sent_to_clay` column | Boolean on `raw.staging_case_study_urls` |
| Added `batch_id` column | Text on `raw.staging_case_study_urls` |
| Added `reference.industry_lookup` row | "Software" → "Software Development" |
| Domain cleanup | 10,982 rows in core.company_customers, 1,861 in staging |
| Backfill customers to core | 1,045 rows from extracted → core.company_customers |
| Backfill case study buyers to core | 4,609 rows from extracted → core.case_study_champions |
| Backfill origin_company_name | 1,014 rows in raw.staging_case_study_urls filled from core tables |

---

## Case Study Extraction Pipeline (Reference)

Two pipelines exist:

### Pipeline 1: case_study_details + case_study_champions (older, Jan 8)
```
case_study_url → ingest_case_study_extraction (Gemini Flash)
    → raw.gemini_case_study_payloads
    → extracted.case_study_details (9,569 rows)
    → extracted.case_study_champions (10,139 rows) → core.case_study_champions
```

### Pipeline 2: case_study_buyers (newer, Jan 29-31)
```
case_study_url → extract_case_study_buyer (Gemini)
    → raw.case_study_buyers_payloads
    → extracted.case_study_buyers (17,924 rows) → core.case_study_champions
```

Both pipelines write to `core.case_study_champions` with different `source` values.

### Staging → Clay → Gemini flow
```
ingest_company_customers_structured
    → raw.staging_case_study_urls (staged, sent_to_clay=false)
        → send_case_study_urls_to_clay (Modal, 10/sec)
            → Clay webhook → Gemini extraction
                → ingest_case_study_extraction OR extract_case_study_buyer
                    → extracted tables → core
                        → mark processed=true in staging
```

---

## Currently In Progress

- None (session ending)

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     api.revenueinfra.com                         │
├─────────────────────────────────────────────────────────────────┤
│  /run/companies/claygent/customers-of-3/ingest                  │
│  /run/case-study-urls/to-clay                                   │
│  /run/companies/case-study-details/lookup                       │
│  /run/companies/companyenrich/ingest                            │
│  /run/* (80+ other endpoints)                                   │
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
│  raw.* → extracted.* → reference.* → core.*                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Connection

```
postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```
