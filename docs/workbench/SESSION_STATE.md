# Session State

**Last updated:** 2026-02-03

This file tracks the current state of work. Update after every major milestone.

---

## Just Completed (Phase 1: API Wrapper Endpoints)

### Run Router - Modal API Wrappers
Created a comprehensive API layer at `api.revenueinfra.com/run/*` that wraps all Modal serverless functions:

- **New file:** `/hq-api/routers/run.py` (~4,400 lines)
- **80 API endpoints** wrapping Modal functions
- **Endpoint naming convention:** `POST /run/{entity}/{provider}/{workflow}/{action}`
  - `entity`: `companies` or `people`
  - `provider`: `clay-native`, `gemini`, `db`, `claygent`, `cb`, etc.
  - `workflow`: descriptive name (e.g., `firmographics`, `icp-criteria`)
  - `action`: `ingest`, `infer`, `lookup`, `upsert`, `backfill`

### Endpoint Categories Added

| Category | Count | Example Path |
|----------|-------|--------------|
| Company Ingestion | ~25 | `/run/companies/clay-native/firmographics/ingest` |
| People Ingestion | ~15 | `/run/people/clay-native/person-profile/ingest` |
| Gemini Inference | ~20 | `/run/companies/gemini/industry/infer` |
| Database Lookups | ~8 | `/run/companies/db/company-customers/lookup` |
| Database Upserts | ~6 | `/run/companies/db/core-company-full/upsert` |
| Backfill Operations | ~4 | `/run/people/db/populate-location/backfill` |
| Signal Ingestion | ~6 | `/run/people/clay-native/signal-job-change-2/ingest` |

### Documentation Created
- **`/docs/api/ENDPOINT_MAPPING.md`** - Maps all 80 workflows from:
  - Workflow slug → Modal function name → Modal URL → API endpoint

### Database Schema Updates
- Added columns to `reference.enrichment_workflow_registry`:
  - `modal_function_name` - Python function name in Modal
  - `modal_endpoint_url` - Full Modal endpoint URL
  - `api_endpoint_url` - API wrapper endpoint path
- Migration: `/supabase/migrations/20260202_add_endpoint_columns.sql`

### Git Commits
- `7dc54c8` - feat: add run router with Modal API wrapper endpoints

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
│  /run/*                │  NEW: Modal function wrappers (80)     │
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

## Currently In Progress

- Nothing active - Phase 1 complete, ready for Phase 2

---

## Blocked / Waiting

- None

---

## Key Files Modified This Session

| File | Changes |
|------|---------|
| `/hq-api/routers/run.py` | NEW - 80 endpoints, ~4,400 lines |
| `/hq-api/main.py` | Added `run` router import |
| `/docs/api/ENDPOINT_MAPPING.md` | NEW - Workflow to endpoint mapping |
| `/supabase/migrations/20260202_add_endpoint_columns.sql` | NEW - Registry columns |

---

## Workflow Registry Status

The `reference.enrichment_workflow_registry` table EXISTS and contains:
- ~106 workflow entries
- New columns: `modal_function_name`, `modal_endpoint_url`, `api_endpoint_url`
- Column `workflow_type` distinguishes: `ingest`, `inference`, `lookup`, `utility`

Query the registry:
```sql
SELECT workflow_slug, modal_function_name, api_endpoint_url
FROM reference.enrichment_workflow_registry
WHERE api_endpoint_url IS NOT NULL
ORDER BY workflow_slug;
```

---

## API Quick Reference

### Test an endpoint
```bash
curl -X POST https://api.revenueinfra.com/run/companies/gemini/industry/infer \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Stripe", "domain": "stripe.com"}'
```

### View all run endpoints
```
https://api.revenueinfra.com/docs#/run
```

### Endpoint timeout conventions
- Standard ingest/lookup: 30-60 seconds
- Gemini inference: 60-90 seconds
- Backfill operations: 600-1800 seconds

---

## Next Priorities (Phase 2)

1. **TBD** - Awaiting direction on next phase
2. Consider: Workflow registry audit (verify all `coalesces_to_core` values)
3. Consider: End-to-end testing of critical workflows
4. Consider: OpenAPI spec regeneration for new endpoints

---

## Key Context for Next Session

- **Run router complete**: 80 Modal functions wrapped at `/run/*`
- **Naming convention**: `/run/{entity}/{provider}/{workflow}/{action}`
- **Some Modal URLs have unique suffixes** (e.g., `-85468a`, `-f1e270`) - use exact URLs
- **Registry updated**: `api_endpoint_url` column populated for wrapped workflows
- **Not yet committed**: Recent endpoint additions since `7dc54c8`
- **Production URL**: `api.revenueinfra.com` (Railway auto-deploys from main)

---

## Database Connection

```
postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```
