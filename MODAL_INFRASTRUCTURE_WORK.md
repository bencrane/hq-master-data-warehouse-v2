# Modal Infrastructure Work Documentation

> **⚠️ ARCHIVED DOCUMENT**  
> This document is from January 6, 2026 and describes a historical infrastructure rebuild.  
> The endpoint limit issue has since been resolved.  
> For current documentation, see [docs/modal-onboarding.md](./docs/modal-onboarding.md).

**Date:** January 6, 2026  
**Status:** Code committed, deployment blocked by endpoint limits (RESOLVED)

---

## Executive Summary

Rebuilt the Modal ingestion infrastructure from scratch after discovering that previous deployments were lost due to:
1. Code never being committed to the repo
2. Deployments happening from temporary worktrees that were cleaned up
3. No single entry point ensuring all functions were deployed together

The new architecture is properly structured with all code committed to `main`. Deployment is currently blocked by Modal's free tier limit of 8 web endpoints.

---

## What Was Lost

The following endpoints were previously working (confirmed by data in database from January 2, 2026) but are now returning 404:

| Endpoint | Status Before | Status Now |
|----------|---------------|------------|
| `ingest-company-payload` | Working | 404 |
| `ingest-person-payload` | Working | 404 |
| `ingest-person-discovery` | Working | 404 |
| `ingest-company-discovery` | Working | 405 (still deployed) |
| `generate-target-client-icp` | Unknown | 404 |

**Root Cause:** A partial redeployment at some point only included `ingest-company-discovery`, which replaced the entire app and removed all other functions.

---

## New File Structure

All code is now in `modal-mcp-server/src/`:

```
modal-mcp-server/src/
├── app.py                    # ENTRY POINT - deploy this file only
├── config.py                 # Shared app and image definition
├── extraction/
│   ├── __init__.py
│   ├── company.py            # extract_company_firmographics, extract_company_discovery
│   └── person.py             # extract_person_profile, extract_person_experience, 
│                             # extract_person_education, extract_person_discovery
├── ingest/
│   ├── __init__.py
│   ├── company.py            # ingest_company_payload, ingest_company_discovery
│   └── person.py             # ingest_person_payload, ingest_person_discovery
└── icp/
    ├── __init__.py
    └── generation.py         # generate_target_client_icp
```

### Key Design Decisions

1. **Single Entry Point (`app.py`)**: All deployments must use `modal deploy app.py`. This file imports all modules, ensuring every function is always deployed together.

2. **Shared Config (`config.py`)**: The Modal `app` and `image` objects are defined once and imported by all modules. This prevents circular imports and ensures consistency.

3. **Lazy Imports**: Heavy dependencies (supabase, openai) are imported inside function bodies, not at module level. This is required because Modal evaluates imports locally before deployment, and those packages may not be installed locally.

4. **No Pydantic at Module Level**: Request validation uses plain `dict` types instead of Pydantic models at the function signature level. Pydantic is available in the Modal image but not locally.

---

## Functions Created

### 1. `ingest_company_payload`
- **Endpoint:** `https://bencrane--hq-master-data-ingest-ingest-company-payload.modal.run`
- **Method:** POST
- **Workflow:** `clay-company-firmographics`
- **Stores to:** `raw.company_payloads` → `extracted.company_firmographics`

### 2. `ingest_company_discovery`
- **Endpoint:** `https://bencrane--hq-master-data-ingest-ingest-company-discovery.modal.run`
- **Method:** POST
- **Workflow:** `clay-find-companies`
- **Stores to:** `raw.company_discovery` → `extracted.company_discovery`

### 3. `ingest_person_payload`
- **Endpoint:** `https://bencrane--hq-master-data-ingest-ingest-person-payload.modal.run`
- **Method:** POST
- **Workflow:** `clay-person-profile`
- **Stores to:** `raw.person_payloads` → `extracted.person_profile`, `extracted.person_experience`, `extracted.person_education`

### 4. `ingest_person_discovery`
- **Endpoint:** `https://bencrane--hq-master-data-ingest-ingest-person-discovery.modal.run`
- **Method:** POST
- **Workflow:** `clay-find-people`
- **Stores to:** `raw.person_discovery` → `extracted.person_discovery`

### 5. `generate_target_client_icp`
- **Endpoint:** `https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run`
- **Method:** POST
- **Workflow:** `ai-generate-target-client-icp`
- **Stores to:** `raw.icp_payloads` → `extracted.target_client_icp`
- **Uses:** OpenAI `gpt-4o-mini`

---

## Deployment Status

### Committed to `main`: ✅
All code has been committed and pushed:
```
commit 3ee9394
"Add Modal ingestion functions with proper file structure"
```

### Deployed to Modal: ❌ BLOCKED

**Error:**
```
Deployment failed: reached limit of 8 web endpoints 
(# already deployed => 7, # in this app => 5)
```

**Current deployed apps:**
| App | State |
|-----|-------|
| case-study-* | deployed |
| data-enrich-* | deployed |
| hq-master-data-ingest | deployed (partial - only 1 endpoint) |

---

## Required Secrets

The Modal functions require these secrets to be configured:

| Secret Name | Required Keys | Used By |
|-------------|---------------|---------|
| `supabase-credentials` | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | All ingest functions |
| `openai-secret` | `OPENAI_API_KEY` | `generate_target_client_icp` |

---

## Next Steps

### Immediate: Resolve Endpoint Limit

**Option A: Stop unused apps**
```bash
modal app stop ap-lkeSeqCsEYVa0nagRlHCZN  # case-study-*
modal app stop ap-fzBuQUP34ut0cpWoQX4OtA  # data-enrich-*
```

**Option B: Upgrade Modal plan**
- Go to: https://modal.com/settings/bencrane/plans
- Free tier: 8 endpoints
- Team tier: 25 endpoints

### After Resolving Limits: Deploy

**IMPORTANT:** The project uses `uv` for dependency management. You MUST run modal commands through `uv run` from the `modal-mcp-server` directory (where `pyproject.toml` lives), NOT from `src/`.

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

Do NOT run `modal deploy` directly - it will fail with `ModuleNotFoundError: No module named 'pydantic'` because the dependencies are managed by uv.

### Verify Deployment

After deployment, verify all endpoints return 405 (Method Not Allowed) for GET requests:
```bash
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-ingest-company-payload.modal.run
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-ingest-person-payload.modal.run
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-ingest-company-discovery.modal.run
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-ingest-person-discovery.modal.run
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run
```

Expected: All return `405` (POST-only endpoints return 405 for GET)

---

## Deployment Rules (Non-Negotiable)

1. **All code committed before deploy** — No exceptions
2. **Always deploy from `app.py`** — Never deploy individual modules
3. **Always deploy from `main` branch** — Check out main first, pull latest
4. **Never deploy from worktrees** — If in detached HEAD, stop and check out main

### Deployment Checklist

```bash
# 1. Ensure on main branch
cd /Users/benjamincrane/hq-master-data-warehouse-v2
git checkout main
git pull origin main

# 2. Verify code is committed
git status  # Should show "nothing to commit, working tree clean"

# 3. Deploy using uv from modal-mcp-server directory
cd modal-mcp-server
uv run modal deploy src/app.py

# 4. Verify endpoints
# (run verification curls above)
```

**Why `uv run`?** The project uses `uv` for dependency management. Running `modal deploy` directly will fail because pydantic and other dependencies are only available in the uv-managed virtual environment.

---

## Database Tables Used

### Raw Tables (JSONB storage)
- `raw.company_payloads`
- `raw.company_discovery`
- `raw.person_payloads`
- `raw.person_discovery`
- `raw.icp_payloads`

### Extracted Tables (Flattened)
- `extracted.company_firmographics`
- `extracted.company_discovery`
- `extracted.person_profile`
- `extracted.person_experience`
- `extracted.person_education`
- `extracted.person_discovery`
- `extracted.target_client_icp`

### Reference Tables
- `reference.enrichment_workflow_registry` — Workflow definitions
- `reference.target_clients` — Target client companies

---

## Workflow Registry

| workflow_slug | provider | entity_type |
|---------------|----------|-------------|
| `clay-company-firmographics` | clay | company |
| `clay-find-companies` | clay | company |
| `clay-person-profile` | clay | person |
| `clay-find-people` | clay | person |
| `ai-generate-target-client-icp` | openai | target_client |

---

## Files Changed in This Session

### Created
- `modal-mcp-server/src/app.py`
- `modal-mcp-server/src/config.py`
- `modal-mcp-server/src/extraction/__init__.py`
- `modal-mcp-server/src/extraction/company.py`
- `modal-mcp-server/src/extraction/person.py`
- `modal-mcp-server/src/ingest/__init__.py`
- `modal-mcp-server/src/ingest/company.py`
- `modal-mcp-server/src/ingest/person.py`
- `modal-mcp-server/src/icp/__init__.py`
- `modal-mcp-server/src/icp/generation.py`

### Previously Existed (Not Modified)
- `modal-mcp-server/src/icp_generation.py` — Old file, can be deleted
- `modal-mcp-server/src/modal_mcp/server.py` — Unrelated MCP server

---

## Known Issues

1. **Endpoint Limit**: Modal free tier only allows 8 web endpoints. Current deployment requires 5 endpoints but 7 are already in use by other apps.

2. **Local Dependencies**: The deploy command requires Modal to be installed locally (`pip install modal`). Heavy dependencies like `supabase` and `openai` are only needed in the Modal image, not locally.

3. **Old Files**: `modal-mcp-server/src/icp_generation.py` is an old standalone file that should be deleted after confirming the new structure works.

---

## Contact

For questions about this infrastructure, reference this document and the `MODAL_ENDPOINTS.md` file which contains detailed payload documentation.

