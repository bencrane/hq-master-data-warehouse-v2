# Modal Changelog

Log of significant changes to Modal infrastructure.

For detailed API documentation, see [MODAL_ENDPOINTS.md](./MODAL_ENDPOINTS.md).

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

### [FIX-001: Person Extraction Column Name Mismatch](./modal-docs/FIX-001-person-extraction-columns.md)

**Status:** ✅ Resolved  
**Affected endpoints:** `ingest-clay-person-profile`  
**Severity:** Critical — extraction completely broken  

Column name mismatch in `extraction/person.py` caused all person profile extraction to fail silently. Raw data was being stored but extraction threw errors due to non-existent column names.

---

## 2026-01-06

### Infrastructure Rebuild

**Status:** ✅ Completed  
**Documentation:** [MODAL_INFRASTRUCTURE_WORK.md](./MODAL_INFRASTRUCTURE_WORK.md) (archived)

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
