# Post-Mortem: Wrong Database Connection & Wrong API URL

**Date:** 2026-02-05
**Severity:** Medium
**Status:** Resolved

---

## What Happened

Two separate careless errors in one session:

### Error 1: Created table on wrong database

Ran `psql "$DATABASE_URL"` to create `public.focus_companies`. The `$DATABASE_URL` env var points to a **different database** than Supabase. The table was created on the wrong database. When Clay sent 161 records to the Modal ingest endpoint, they all failed silently because the table didn't exist on Supabase.

Had to recreate the table on Supabase using the correct connection string and ask the user to resend from Clay.

### Error 2: Told frontend the wrong API URL

Told the user the endpoint was at `POST https://api.revenueinfra.com/api/read/companies/coverage`. The FastAPI app has no `/api` prefix — all routers mount directly at root. The correct URL is `POST https://api.revenueinfra.com/read/companies/coverage`. Frontend hit 404.

---

## Root Cause

1. **Assumed `$DATABASE_URL` pointed to Supabase.** It doesn't. The correct connection string is hardcoded in CLAUDE.md and should always be used directly.

2. **Assumed an `/api` prefix existed.** Didn't verify by checking `main.py` or testing the URL before telling the user. The app mounts routers without any global prefix.

---

## What Should Have Been Done

1. **Always use the Supabase connection string directly:**
   ```
   psql "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"
   ```
   Never use `$DATABASE_URL`. This is already documented in CLAUDE.md — the documentation was ignored.

2. **Always verify endpoint URLs before reporting them.** Run a quick `curl` test before telling the user or the frontend agent what URL to hit.

---

## Fixes Applied

1. Recreated `public.focus_companies` on the correct Supabase database
2. Updated CLAUDE.md with explicit warning about never using `$DATABASE_URL`
3. Updated ONBOARDING.md with the same rule
4. Added to Common Gotchas in CLAUDE.md

---

## Lesson

Read your own documentation. Both errors were preventable by following rules that were already written down.
