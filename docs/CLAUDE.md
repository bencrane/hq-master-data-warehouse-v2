# Claude Context - HQ Master Data Warehouse

Quick-reference for Claude Code sessions.

---

## Start of Session Protocol

**New session or memory compressed?** Read in this order:

1. **This file** (CLAUDE.md) — Project context
2. **[SESSION_STATE.md](./workbench/SESSION_STATE.md)** — What was just done, what's in progress, what's next
3. **[/docs/workbench/README.md](./workbench/README.md)** — Current priorities
4. **Ask user** what they want to focus on

Full onboarding checklist: **[ONBOARDING.md](./ONBOARDING.md)**

---

## Project Summary

**What:** B2B lead intelligence platform aggregating people and company data from multiple sources (Clay, Apollo, LinkedIn SalesNav).

**Stack:** FastAPI (Python) + PostgreSQL (Supabase) + Next.js 16 + Modal (serverless)

**Architecture:** Database owns all business logic. API is a thin layer. 4-schema data flow: `raw` -> `extracted` -> `reference` -> `core`.

---

## Key Locations

| What | Where |
|------|-------|
| **Active work / TODOs** | `/docs/workbench/` |
| **API code** | `/hq-api/` (FastAPI) |
| **Frontend code** | `/frontend/` (Next.js) |
| **Data pipelines** | `/modal-functions/` |
| **Database migrations** | `/supabase/migrations/` |
| **Architecture docs** | `/docs/architecture/` |
| **Workflow docs** | `/docs/workflows/` |

---

## Database Connection

```
postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```

**IMPORTANT:** Always use this connection string for ALL psql commands. Never use `$DATABASE_URL` or any other env variable — it may point to a different database. Hardcode this string in every psql call.

**Supabase URL:** `https://ivcemmeywnlhykbuafwv.supabase.co`

---

## Production URLs

| Service | URL |
|---------|-----|
| **API (production)** | `https://api.revenueinfra.com` |
| **API (Railway direct)** | `https://hq-master-data-api-production.up.railway.app` |
| **Frontend** | `https://app.revenueinfra.com` |

Example API call:
```
https://api.revenueinfra.com/api/enrichment/workflows
```

---

## Core Principles (Summary)

1. **Database owns business logic** - All joins, filters, aggregations in PostgreSQL views/functions
2. **Thin API layer** - Endpoints < 20 lines, call DB once
3. **Explicit columns** - Never SELECT *, define column constants
4. **Views for simple, functions for complex** - Most queries use views
5. **Single source of truth** - `core.leads` is the canonical leads view

---

## Self-Annealing Behavior

**This is not optional.** When completing work, update relevant documentation immediately:

| When I... | I must... |
|-----------|-----------|
| Encounter an error | Add to Troubleshooting or Edge Cases in the relevant doc |
| Discover an API quirk or timing issue | Document it where future sessions will find it |
| Find a better approach | Add to Learnings section |
| Complete a workflow | Verify the doc reflects current reality |
| Fix a bug | Document the root cause and fix |

**The goal:** Knowledge stays in the repo, not in chat transcripts. Each session makes the system smarter. Don't just fix — capture the fix.

**Where to document:**
- Workflow-specific learnings → `/docs/workflows/catalog/[workflow].md`
- API/system-wide learnings → `/docs/CLAUDE.md` (Common Gotchas) or `/docs/architecture/`
- Active work discoveries → `/docs/workbench/TODO.md` or the active task file

**After completing a major milestone:**
1. Update `SESSION_STATE.md` with what was completed
2. Move items from "In Progress" to "Just Completed"
3. Update "Next Priorities" if needed
4. Add any "Key Context for Next Session" notes

This ensures the next session (or a fresh instance) knows exactly where things stand.

---

## Schema Overview

| Schema | Purpose | Example Tables |
|--------|---------|----------------|
| `raw` | Unmodified JSON payloads | `raw.claygent_*_raw` |
| `extracted` | Flattened, one row per entity | `extracted.person_experience` |
| `reference` | Lookup catalogs | `reference.job_functions`, `reference.technologies` |
| `core` | Normalized domain data | `core.leads`, `core.companies_full`, `core.person_work_history` |

---

## API Endpoint Pattern

```python
@router.get("/endpoint")
async def get_something(
    param: str = Query(...),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Docstring."""
    pool = get_pool()
    rows = await pool.fetch("SELECT * FROM core.view_or_function($1)", param)
    return {"data": [dict(r) for r in rows], "meta": {"total": len(rows), "limit": limit, "offset": offset}}
```

---

## Current Priorities

Check `/docs/workbench/README.md` for current session priorities.

Check `/docs/workbench/TODO.md` for the full task list.

---

## Common Gotchas

1. **ALWAYS use the Supabase connection string** - Never use `$DATABASE_URL` for psql. Always use: `postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres`
2. **Modal deploy** - Always use `cd modal-functions && uv run modal deploy src/app.py` (not bare `modal deploy`)
3. **Modal secrets** - If data isn't appearing, check Modal secrets match Supabase project (`modal secret show supabase-credentials`)
4. **PostgREST timeouts** - Use asyncpg for function calls, not Supabase client
5. **PostgREST schema exposure** - If a schema isn't accessible via the Supabase client, tell the user to expose it in Supabase dashboard (API settings > Exposed schemas). Don't use RPC/raw SQL workarounds.
6. **API required fields** - Leads must have: `company_name`, `company_country`, `person_country`, `matched_job_function`, `matched_seniority` to appear in dashboard
7. **Enrichment gaps** - Data in `extracted` may not be in `core` (no automatic sync)
8. **GitHub push auto-deploys Railway** - The frontend is in a separate repo. Push to this repo deploys the API only.

---

## Key Files

| File | Purpose |
|------|---------|
| `/hq-api/main.py` | FastAPI app entry point |
| `/hq-api/db.py` | Database connection helpers |
| `/hq-api/routers/leads.py` | Core leads endpoints |
| `/frontend/lib/api.ts` | Frontend API client |
| `/modal-functions/src/app.py` | Modal app configuration |

---

## Quick Commands

```bash
# Start API locally
cd hq-api && uvicorn main:app --reload --port 8000

# Start frontend locally
cd frontend && npm run dev

# Deploy Modal functions (MUST use uv run)
cd modal-functions && uv run modal deploy src/app.py

# Regenerate OpenAPI spec (use .venv python)
cd hq-api && .venv/bin/python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > openapi.json
```
