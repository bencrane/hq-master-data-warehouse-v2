# Handoff: Leads API Investigation

**Date:** 2026-01-28
**Status:** In Progress - Investigation Phase

---

## Context

The frontend dashboard shows 0 leads. The issue is the HQ API's `/api/leads` endpoint returning 500 errors.

## What Was Already Done

1. **Similar companies batch COMPLETED** - 598/598 domains, 1000 similar companies found
2. **Fixed `db.py`** - Changed `core()` to return `supabase.schema("core")` instead of default public schema
3. **Added error handling** to leads endpoint to surface actual errors
4. **Committed and pushed** changes to GitHub (commits: `1bf2d03`, `20a6b85`)

## Current Finding

The actual error is now visible:
```
{"detail":"Database error: {'message': 'JSON could not be generated', 'code': 500, 'hint': 'Refer to full message for details', 'details': \"b''\"}"
```

## Investigation Results So Far

1. **`core.leads` view EXISTS** and has all expected columns
2. **Direct REST API query WORKS:**
   ```bash
   curl -s "https://ivcemmeywnlhykbuafwv.supabase.co/rest/v1/leads?limit=1" \
     -H "apikey: [SERVICE_KEY]" \
     -H "Accept-Profile: core"
   ```
   Returns valid JSON with lead data.

3. **Count query WORKS** - 1,465,032 leads in the view

4. **The issue is likely** the combination of filters the API applies via `apply_lead_filters()` in `hq-api/routers/leads.py`

## Next Steps to Complete

1. **Test the exact filter combination** the API uses:
   - The API applies these filters on EVERY request (lines 39-47 of leads.py):
     ```python
     query = query.not_.is_("company_name", "null")
     query = query.not_.is_("company_country", "null")
     query = query.not_.is_("person_country", "null")
     query = query.not_.is_("matched_job_function", "null")
     query = query.not_.is_("matched_seniority", "null")
     query = query.not_.is_("matched_cleaned_job_title", "null")
     query = query.not_.is_("matched_industry", "null")
     query = query.neq("matched_job_function", "Miscellaneous")
     ```

2. **Identify which filter causes the "JSON could not be generated" error**

3. **Fix the filter or query approach**

## Key Files

- `hq-api/routers/leads.py` - The leads endpoint code
- `hq-api/db.py` - Database connection (already fixed)
- `hq-api/CHANGELOG.md` - Documents that API was working on 2026-01-25

## Supabase Credentials (from .env)

```
SUPABASE_URL=https://ivcemmeywnlhykbuafwv.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2Y2VtbWV5d25saHlrYnVhZnd2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MTUyMzkyNSwiZXhwIjoyMDc3MDk5OTI1fQ.pAM4IxESDuROXU0Rn-O9VDjLldyLDrE2SJ7F3_dq46o
```

## Test Commands

Test direct API (should work):
```bash
curl -s "https://ivcemmeywnlhykbuafwv.supabase.co/rest/v1/leads?limit=1" \
  -H "apikey: [SERVICE_KEY]" \
  -H "Accept-Profile: core"
```

Test HQ API (currently failing):
```bash
curl -s 'https://hq-master-data-api-production.up.railway.app/api/leads?limit=1'
```

## DO NOT

- Make code changes without understanding root cause
- Deploy without testing
- Ignore the investigation plan
