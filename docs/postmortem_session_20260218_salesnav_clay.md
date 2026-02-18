# Post-Mortem: SalesNav Clay Ingestion Endpoint Failure

**Date:** 2026-02-18
**Session Duration:** ~1 hour
**Outcome:** Partial implementation with multiple failed deploys, user lost confidence

---

## Summary

User requested implementation of a Modal endpoint to ingest SalesNav person data from Clay webhooks. A detailed plan was provided with exact tables, field mappings, and data flow. Despite having a clear plan, the implementation required 4+ deploy cycles to fix avoidable errors.

---

## What Was Requested

A straightforward endpoint following the existing raw → extracted → core pattern:

| Layer | Table | Purpose |
|-------|-------|---------|
| Raw | `raw.salesnav_scrapes_person_payloads` | Store full Clay payload |
| Extracted | `extracted.salesnav_scrapes_person` | Flattened person fields |
| Extracted | `extracted.salesnav_scrapes_companies` | Flattened company fields |
| Core | `core.companies` | Upsert company record |
| Core | `core.company_linkedin_urls` | Store company LinkedIn URL |
| Core | `core.person_past_employer` | Alumni relationship |

---

## Failures

### 1. Did Not Verify Database Constraints Before Writing Code

**What happened:** First deployment failed with:
```
there is no unique or exclusion constraint matching the ON CONFLICT specification
```

**Why:** Used `on_conflict="linkedin_url,past_company_domain"` but the actual constraint in `20260128_core_person_past_employer.sql` is on THREE columns:
```sql
UNIQUE (linkedin_url, past_company_name, past_company_domain)
```

**Should have done:** Read the migration file BEFORE writing the upsert code.

### 2. Incomplete Implementation - Missed Core Tables

**What happened:** Initial implementation only wrote to:
- `raw.salesnav_scrapes_person_payloads`
- `extracted.salesnav_scrapes_person`

User had to explicitly ask: "What about core.companies? What about extracted.salesnav_scrapes_companies?"

**Why:** Did not fully read the plan before implementing.

**Should have done:** Follow the plan exactly. The plan clearly listed ALL target tables.

### 3. Did Not Understand Domain Context

**What happened:** User had to explain that SalesNav LinkedIn URLs are hashed/sales-specific, not real LinkedIn profile URLs.

**Why:** Did not read existing code (`salesnav_person.py`, `salesnav_person_full.py`) to understand how they handle this.

**Should have done:** Study existing similar endpoints to understand domain nuances.

### 4. Wasted Time on Local Database Queries

**What happened:** Spent multiple attempts trying to query a local database that doesn't have the production schema, getting errors like:
```
relation "raw.salesnav_scrapes_person_payloads" does not exist
```

**Why:** Didn't recognize that the local `DATABASE_URL` points to a different database than Modal's production Supabase instance.

**Should have done:** Use Supabase REST API immediately, or ask user for correct connection method.

### 5. Overcomplicated Record Deletion

**What happened:** User asked to delete test records. Instead of a simple approach, fumbled with:
- Multiple curl DELETE requests
- Supabase REST API pagination limits (4 records per request)
- Loop syntax errors
- Still didn't successfully delete all records

**Why:** Did not know Supabase REST API delete limits. Did not use a proper SQL connection.

**Should have done:** Ask user for preferred deletion method, or use `psql` with correct production connection string.

### 6. Multiple Failed Deploy Cycles

Each fix required another deploy because errors were discovered only after testing:

1. Deploy 1: Constraint mismatch error
2. Deploy 2: Missing `core.companies` upsert
3. Deploy 3: Missing `extracted.salesnav_scrapes_companies`
4. Deploy 4: (User lost patience before further testing)

---

## Root Cause Analysis

### Primary Cause: Did Not Read Before Writing

The plan provided exact table names, field mappings, and data flow. Existing code in `salesnav_person.py` and `salesnav_person_full.py` showed the established patterns. Migration files in `supabase/migrations/` contained exact schema definitions.

Instead of reading these thoroughly, code was written speculatively and debugged iteratively.

### Secondary Cause: Did Not Ask Clarifying Questions

- What is the exact constraint on `core.person_past_employer`?
- Is the LinkedIn URL from SalesNav a real profile URL or hashed?
- What's the correct way to connect to the production database locally?

These questions would have saved multiple deploy cycles.

---

## Correct Approach (For Future AI Instances)

### Before Writing Any Code:

1. **Read the plan completely** - Don't skim. Every table, field, and constraint mentioned is intentional.

2. **Read existing similar code** - For this task:
   - `modal-functions/src/ingest/salesnav_person.py`
   - `modal-functions/src/ingest/salesnav_person_full.py`
   - `modal-functions/src/extraction/salesnav_person.py`

3. **Read migration files for ALL target tables**:
   ```bash
   grep -r "CREATE TABLE.*table_name" supabase/migrations/
   ```
   Check constraints, column names, and types.

4. **Ask clarifying questions** if anything is unclear about:
   - Business logic (e.g., what does "hashed LinkedIn URL" mean?)
   - Database schema (e.g., what's the unique constraint?)
   - Environment (e.g., how to connect to production DB?)

### When Implementing:

5. **Implement ALL tables in the plan in one pass** - Don't do partial implementations.

6. **Test constraint names match** - If using `on_conflict`, verify the constraint exists with that exact column list.

7. **Use correct database connection** - For this codebase, Supabase REST API via curl works:
   ```bash
   export $(grep -v '^#' .env | xargs)
   curl -s "${SUPABASE_URL}/rest/v1/table_name" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Accept-Profile: schema_name"
   ```

### When Errors Occur:

8. **Read the error message carefully** - The constraint error explicitly said what was wrong.

9. **Fix completely before redeploying** - Don't deploy partial fixes.

---

## Files Created/Modified

### Created:
- `modal-functions/src/extraction/salesnav_clay.py`
- `modal-functions/src/ingest/salesnav_clay_ingest.py`

### Modified:
- `modal-functions/src/app.py` (added imports)

### Current State:
- Endpoint is deployed but not fully tested
- Test records still exist in database (deletion incomplete)

---

## Lessons for Future Sessions

1. **Thoroughness over speed** - Taking 10 extra minutes to read existing code saves 60 minutes of debugging.

2. **The plan is the spec** - If the user provides a detailed plan, follow it exactly. Don't improvise.

3. **Ask questions early** - Uncertainty at the start becomes errors at deployment.

4. **One complete implementation > multiple partial fixes** - Users lose confidence with each failed deploy.

5. **Know the environment** - Understand how to connect to databases, run tests, and verify results BEFORE writing code.
