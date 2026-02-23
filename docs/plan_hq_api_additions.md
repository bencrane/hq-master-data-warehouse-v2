# Plan: Add FastAPI Endpoints to hq-api

## Current State
- Reverted to commit `c5720e3` (feat: re-add linkedin-url lookup endpoint)
- All existing Modal functions are working as they were before
- Database changes (job_function, city, state, country columns, job_board_domains table) are intact

## Existing Modal Endpoints (WORKING - DO NOT TOUCH)
These already work via Modal:
- `infer-revenue-db-direct`
- `infer-funding-db-direct`
- `infer-employees-db-direct`
- `infer-last-funding-date-db-direct`
- `infer-description-db-direct`
- `infer-g2-url-db-direct`

## Goal
Add FastAPI endpoints to `hq-api/` for:
1. **NEW** Parallel AI enrichments (hq-location, industry, competitors) - these don't exist yet
2. Job boards API (serves white-label job board sites)

## What We Will NOT Touch
- `modal-functions/` directory - NO CHANGES
- `/modal/` directory - NO CHANGES
- Any Modal-related code
- Existing working Modal endpoints

---

## Step 1: Create `hq-api/routers/parallel_native.py`

**Purpose:** FastAPI endpoints for NEW Parallel AI enrichments only (not duplicating existing Modal ones).

**Endpoints:**
| Method | Path | Description | Writes To |
|--------|------|-------------|-----------|
| POST | `/parallel-native/hq-location` | Infer company HQ location | `core.company_parallel_locations` |
| POST | `/parallel-native/industry` | Infer company industry | `core.company_parallel_industries` |
| POST | `/parallel-native/competitors` | Infer company competitors | `core.company_parallel_competitors` |

**Dependencies:**
- `httpx` (already in requirements.txt)
- `PARALLEL_API_KEY` environment variable

---

## Step 2: Create `hq-api/routers/job_boards.py`

**Purpose:** API for white-label job board domains (salesopsjobs.com, etc.)

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/job-boards/jobs/{domain}` | Get jobs for a domain with company enrichment |
| GET | `/job-boards/jobs/{domain}/stats` | Get job statistics for a domain |
| GET | `/job-boards/domains` | List all configured job board domains |

**Data Flow:**
1. Look up domain in `reference.job_board_domains` → get job_functions
2. Query `core.company_job_postings` filtered by job_functions
3. Join with company enrichment tables (descriptions, revenue, funding, employees)
4. Return combined results

---

## Step 3: Update `hq-api/main.py`

**Changes:**
```python
# Add to imports
from routers import ..., parallel_native, job_boards

# Add router includes
app.include_router(parallel_native.router)
app.include_router(job_boards.router)
```

---

## Step 4: Update `hq-api/.env` (local)

Add:
```
PARALLEL_API_KEY=LBGQ8CjfxZfPqqA7g1BDQS-_ci0BWtzeznqyDR6m
```

---

## Step 5: Test Locally

```bash
cd hq-api
source .venv/bin/activate
python -c "from main import app; print('OK')"
```

---

## Step 6: Commit and Push

```bash
git add hq-api/routers/parallel_native.py hq-api/routers/job_boards.py hq-api/main.py
git commit -m "feat: add parallel-native and job-boards FastAPI endpoints"
git push origin main
```

---

## Step 7: Add Railway Environment Variable

Add to Railway `hq-master-data-api` service:
```
PARALLEL_API_KEY=LBGQ8CjfxZfPqqA7g1BDQS-_ci0BWtzeznqyDR6m
```

---

## Step 8: Verify Deployment

Test endpoints:
```bash
curl https://api.revenueinfra.com/health
curl https://api.revenueinfra.com/job-boards/domains
```

---

## Files Changed Summary

| File | Action |
|------|--------|
| `hq-api/routers/parallel_native.py` | CREATE |
| `hq-api/routers/job_boards.py` | CREATE |
| `hq-api/main.py` | MODIFY (2 lines) |
| `hq-api/.env` | MODIFY (1 line, local only) |

**Total changes:** 3 files in `hq-api/` only. Zero Modal changes.

---

## Rollback Plan

If deployment fails:
```bash
git revert HEAD
git push origin main
```

This only reverts the hq-api changes, leaving everything else intact.
