# TODO - Items to Revisit

## Open Issues

### 1. Modal Secret Misconfiguration (High Priority)
**Date:** 2026-01-31
**Status:** Unresolved

**Problem:** Modal function `ingest_company_customers_v2` is writing to a different Supabase project than expected. Webhook returns success but records don't appear in the database.

**Evidence:**
- Webhook returned success with `raw_id: 3e1d7aca-f8a5-4924-b714-28e65e7cda81`
- Record not found in `raw.claygent_customers_v2_raw`
- ~223 records sent but 0 new records in database since Jan 29

**Action Required:**
1. Run `modal secret show supabase-credentials`
2. Verify `SUPABASE_URL` matches: `https://ivcemmeywnlhykbuafwv.supabase.co`
3. If different, update the Modal secret with correct credentials

**Affected Endpoint:** `modal-functions/src/ingest/company_customers_v2.py`

---

## Completed Items

### Domain Cleanup (2026-01-31)
- [x] Updated `careersatdoordash.com` → `doordash.com` across all schemas
- [x] Updated `aboutamazon.com` → `amazon.com` across all schemas

---

## Notes

- Always use direct PostgreSQL connection for database work:
  ```
  postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
  ```
- `openapi.json` regenerated 2026-01-31 (39 endpoints, all functional)
