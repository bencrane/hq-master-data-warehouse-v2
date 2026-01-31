# Modal Changelog

Log of significant changes to Modal infrastructure.

For detailed API documentation, see [MODAL_ENDPOINTS.md](./MODAL_ENDPOINTS.md).
For onboarding, see [modal-onboarding.md](./modal-onboarding.md).

---

## 2026-01-31

### Endpoint Rewrite: ingest_company_customers_structured

Completely rewrote the endpoint to accept a **flat payload structure** instead of nested `claygent_output`. This fixed issues where Clay was sending structured data that wasn't being parsed correctly.

**New payload format:**
```json
{
  "origin_company_domain": "andela.com",
  "origin_company_name": "Andela",
  "response": "...",
  "customers": [{"url": "...", "companyName": "Resy", "hasCaseStudy": true}],
  "reasoning": "...",
  "confidence": "high",
  "stepsTaken": [...]
}
```

- Endpoint now accepts raw `dict` instead of Pydantic model
- Handles both nested and flat formats
- Properly extracts customers to `extracted.claygent_customers_structured`

### Data Coalescing

- Coalesced **9,004+ records** from `extracted.claygent_customers_structured` to `core.company_customers`
- Used direct postgres connection for bulk INSERT with `ON CONFLICT DO NOTHING`

### Case Study Buyer Extraction

- Tested `gemini-2.0-flash-lite` as alternative model (poor domain extraction results)
- Reverted to `gemini-2.5-flash-lite` which performs significantly better
- Processed 12,392 raw case study records → 12,972 extracted buyers

### Database Stats (end of session)

- `extracted.claygent_customers_structured`: 11,406 records
- `core.company_customers`: 9,000+ records
- `raw.case_study_buyers_payloads`: 12,392 records
- `extracted.case_study_buyers`: 12,972 records
- Snowflake alumni in DB: 952 (past_employer) / 1,367 (work_history)

### hq-api Changes

- Added `POST /api/companies/check-has-customers` endpoint (accepts domain via payload, strips trailing slashes)

---

## 2026-01-24

### Documentation Overhaul

- Created `docs/modal-onboarding.md` - master onboarding document
- Created `docs/modal-development-guide.md` - how to build endpoints
- Rewrote `MODAL_ENDPOINTS.md` - comprehensive endpoint reference
- Marked `MODAL_CODE_VERIFICATION.md` as archived
- Marked `MODAL_INFRASTRUCTURE_WORK.md` as archived

### New Endpoints

- `backfill_person_location` - batch update person locations from lookup
- `ingest_clay_company_location_lookup` - insert company location to lookup table
- `ingest_clay_person_location_lookup` - insert person location to lookup table

### New Tables

- `reference.clay_find_companies_location_lookup`
- `reference.clay_find_people_location_lookup`

---

## 2026-01-23

### New Endpoints

- `ingest_vc_portfolio` - ingest VC portfolio companies with domain matching
- Added `cleaned_first_name`, `cleaned_last_name`, `cleaned_full_name` to `ingest_clay_find_people`

### Data Normalization

- Stripped `www.` prefix from all domain fields across tables

---

## 2026-01-21

### Signal Endpoints

- `ingest_clay_signal_new_hire`
- `ingest_clay_signal_news_fundraising`
- `ingest_clay_signal_job_posting`
- `ingest_clay_signal_job_change`
- `ingest_clay_signal_promotion`

### Lookup Endpoints

- `lookup_person_location`
- `lookup_salesnav_location`
- `lookup_salesnav_company_location`
- `lookup_job_title`

---

## 2026-01-07

### [FIX-001: Person Extraction Column Name Mismatch](./modal-fixes/FIX-001-person-extraction-columns.md)

**Status:** ✅ Resolved  
**Affected endpoints:** `ingest-clay-person-profile`  
**Severity:** Critical — extraction completely broken  

Column name mismatch in `extraction/person.py` caused all person profile extraction to fail silently. Raw data was being stored but extraction threw errors due to non-existent column names.

---

## 2026-01-06

### Infrastructure Rebuild

**Status:** ✅ Completed  
**Documentation:** [MODAL_INFRASTRUCTURE_WORK.md](./MODAL_INFRASTRUCTURE_WORK.md) (archived, in docs/)

Rebuilt Modal ingestion infrastructure from scratch after discovering previous deployments were lost. Established new architecture with single entry point (`app.py`), proper module structure, and deployment rules.

---

## Format Guide

When adding entries:

```markdown
## YYYY-MM-DD

### Category Name

Brief description of changes.

- Bullet points for specific items
- Link to detailed docs if applicable: [Doc Name](./path/to/doc.md)
```

Categories:
- **New Endpoints** - New functions added
- **Modified Endpoints** - Changes to existing functions
- **Bug Fixes** - Link to FIX-* document
- **Database Changes** - New tables, columns, migrations
- **Documentation** - Doc updates
- **Infrastructure** - Deployment, config changes
