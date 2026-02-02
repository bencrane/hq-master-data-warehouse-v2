# Session State

**Last updated:** 2026-02-02

This file tracks the current state of work. Update after every major milestone.

---

## Just Completed

- Regenerated `/hq-api/openapi.json`
- Updated CLAUDE.md with production URLs (`api.revenueinfra.com`)
- Fixed openapi.json regeneration command to use `.venv/bin/python`

---

## Currently In Progress

- Nothing active

---

## Blocked / Waiting

- **Workflow registry table does not exist** — `reference.enrichment_workflow_registry` table needs to be created. The documentation says 106 workflows are registered, but the table doesn't exist in the database. Need to create the table and populate it.

- **Modal secret misconfiguration** — `ingest_company_customers_v2` writing to wrong Supabase project. Needs manual verification of Modal secrets.

---

## Critical Context: Workflow Registry

**The `reference.enrichment_workflow_registry` table does NOT exist in the database.**

Previous session documentation claimed 106 workflows were registered, but querying the database shows:
- `reference` schema only has `countries` table
- No `enrichment_workflow_registry` table exists

To create the registry:
1. Need to create the table schema (see migration files for expected columns)
2. Insert workflow records
3. The endpoint `/api/enrichment/workflows` exists but will fail without the table

**API endpoint for workflows:**
```
https://api.revenueinfra.com/api/enrichment/workflows
```

---

## Next Priorities

1. Create `reference.enrichment_workflow_registry` table
2. Populate registry with workflow metadata
3. Test the `/api/enrichment/workflows` endpoint

---

## Key Context for Next Session

- Production API URL is `api.revenueinfra.com` (not the Railway URL)
- The workflow registry table doesn't exist - needs to be created from scratch
- There are ~87 Modal ingest functions in `/modal-functions/src/ingest/`
- OpenAPI spec was regenerated at `/hq-api/openapi.json`
