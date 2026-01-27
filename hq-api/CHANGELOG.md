# HQ API Changelog

This document records key updates, decisions, and project milestones. Written for continuity across sessions and contributors.

---

## 2026-01-25

### Update 001: Project Initialized

**What was done:**
- Created FastAPI application structure in `/hq-api/`
- Established database connection to Supabase with schema helpers (`core()`, `raw()`, `extracted()`)
- Built core `/api/leads` endpoint with 16 filter parameters
- Built signal endpoints: `/api/leads/new-in-role`, `/api/leads/recently-promoted`, `/api/leads/at-vc-portfolio`
- Built filter endpoints for all dropdown values (job-functions, seniorities, industries, etc.)
- Created database views: `core.leads_recently_promoted`, `core.leads_at_vc_portfolio`

**Key decision: Database-first architecture**
- All business logic lives in PostgreSQL (views and functions)
- FastAPI is a thin routing layer only
- Complex queries use PostgreSQL functions, not Python logic
- This was chosen over application-level query building to avoid URL length limits, ensure consistency, and enable direct SQL testing

**Key decision: Explicit column selection**
- Never use `SELECT *` - Supabase REST API has serialization issues with some views
- Define column lists as constants (e.g., `LEAD_COLUMNS`)
- This also documents the API contract explicitly

**Blocking issue identified:**
- `/api/leads/by-past-employer` endpoint requires PostgreSQL function
- Current workaround (limiting to 500 URLs) violates architecture principles
- Next step: Create `core.get_leads_by_past_employer()` function

**Files created:**
```
hq-api/
├── main.py
├── db.py
├── models.py
├── routers/leads.py
├── routers/filters.py
├── requirements.txt
├── railway.toml
├── API_PLAN.md
├── ARCHITECTURE_PRINCIPLES.md
├── PROJECT_PLAN.md
```

**Endpoints working:**
| Endpoint | Status | Records |
|----------|--------|---------|
| GET /api/leads | Working | 1,336,243 |
| GET /api/leads/new-in-role | Working | 143,084 (180 days) |
| GET /api/leads/recently-promoted | Working | - |
| GET /api/leads/at-vc-portfolio | Working | 1,525,411 |
| GET /api/leads/by-past-employer | Blocked | Needs function |
| GET /api/filters/* | Working | All 7 endpoints |

**Commit:** `ab0ea9c`

---

## 2026-01-26

### Update 002: Stage 4 Complete - Compound Query Endpoints with asyncpg

**What was done:**

1. **Created PostgreSQL functions for compound queries:**
   - `core.get_leads_by_past_employer(p_domains TEXT[], p_limit INT, p_offset INT)` - finds leads who previously worked at specified company domains by joining `core.person_work_history` with `core.leads`
   - `core.get_leads_by_company_customers(p_company_domain TEXT, p_limit INT, p_offset INT)` - finds leads who worked at customers of a specified company
   - Public wrapper functions in `public` schema to expose via Supabase API

2. **Created `core.company_customers` table:**
   - Consolidated customer data from `raw.manual_company_customers` and `raw.company_customer_claygent_payloads`
   - Schema: `origin_company_domain`, `origin_company_name`, `customer_name`, `customer_domain`, `case_study_url`, `has_case_study`, `source`
   - Example: forethought.ai has customers like Upwork, YNAB tracked in this table

3. **Refactored API endpoints to use RPC:**
   - `/api/leads/by-past-employer?domains=salesforce.com` - returns 9,777 leads
   - `/api/leads/by-company-customers?company_domain=forethought.ai` - returns 3,825 leads
   - Renamed from `/by-client-customers` to `/by-company-customers` (clearer terminology - "client" implies business relationship, "company" is just data)

4. **CRITICAL: Refactored from PostgREST to asyncpg for function calls:**
   - PostgREST (Supabase Python client's `.rpc()`) has hard-coded statement timeout (~2s) that cannot be overridden
   - Complex queries like `get_leads_by_company_customers` take ~1.5s, causing intermittent timeouts
   - Solution: Use `asyncpg` for direct PostgreSQL connections when calling functions
   - Supabase client still used for simple table queries (convenience)

**Key architectural decision: Database Connection Strategy**

Updated `ARCHITECTURE_PRINCIPLES.md` to document:

| Query Type | Connection Method | Why |
|------------|-------------------|-----|
| Simple table queries | Supabase client | Convenience, fine for basic CRUD |
| PostgreSQL functions | **asyncpg (direct)** | Full timeout control, no PostgREST limitations |

This is now the canonical pattern. PostgREST adds an unnecessary middleware layer for function calls that introduces timeout constraints we cannot control.

**Implementation details:**

- `db.py`: Added `asyncpg` connection pool with `init_pool()`, `close_pool()`, `get_pool()`
- `main.py`: Added FastAPI lifespan handler to initialize/close pool on startup/shutdown
- `routers/leads.py`: Endpoints use `pool.fetch()` and `pool.fetchrow()` instead of `supabase.rpc()`
- `row_to_dict()` helper converts asyncpg's UUID objects to strings for Pydantic models
- `DATABASE_URL` environment variable required on Railway (PostgreSQL connection string from Supabase)

**Environment variables required:**
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

**Performance optimizations applied:**
- Added indexes: `idx_company_customers_origin_domain`, `idx_company_customers_customer_domain`
- Rewrote `get_leads_by_company_customers` with CTEs and early LIMIT application
- Query time reduced from >4s to ~1.5s

**Issues encountered and resolved:**

1. **PostgREST timeout** - Functions worked when tested directly but timed out via API. Root cause: PostgREST has ~2s statement timeout. Resolution: Migrated to asyncpg.

2. **Railway deployment not updating** - `railway up` wasn't deploying new code. Resolution: Service was connected to GitHub; needed to trigger deploy from latest commit.

3. **UUID serialization** - asyncpg returns UUID objects, Pydantic expects strings. Resolution: Added `row_to_dict()` helper that converts UUIDs to strings.

4. **DATABASE_URL format** - Initially tried using SUPABASE_URL (https://...) for asyncpg. Resolution: Need PostgreSQL connection string (postgresql://...).

**Files changed:**
```
hq-api/db.py                  - Added asyncpg pool management
hq-api/main.py                - Added lifespan for pool init/close
hq-api/routers/leads.py       - Refactored to use asyncpg, added row_to_dict()
hq-api/requirements.txt       - Added asyncpg>=0.29.0
hq-api/ARCHITECTURE_PRINCIPLES.md - Documented connection strategy
```

**Database objects created:**
```sql
-- Functions
core.get_leads_by_past_employer(TEXT[], INT, INT)
core.get_leads_by_company_customers(TEXT, INT, INT)
public.get_leads_by_past_employer(TEXT[], INT, INT)  -- wrapper
public.get_leads_by_company_customers(TEXT, INT, INT)  -- wrapper

-- Table
core.company_customers

-- Indexes
idx_company_customers_origin_domain
idx_company_customers_customer_domain
```

**Endpoints working:**
| Endpoint | Status | Records |
|----------|--------|---------|
| GET /api/leads/by-past-employer | Working | 9,777 (salesforce.com) |
| GET /api/leads/by-company-customers | Working | 3,825 (forethought.ai) |

**Commits:** `a7ce465`, `3815bba`, `b307915`

---

## Template for Future Updates

```markdown
### Update XXX: [Title]

**What was done:**
- Bullet points of completed work

**Key decisions (if any):**
- Decision made and rationale

**Issues encountered (if any):**
- Problem and resolution

**Blocking issues (if any):**
- What's blocked and what's needed

**Files changed:**
- List of files

**Commit:** `xxxxxxx`
```

---

## How to Use This Document

1. **Add an update** after completing a stage, project, or significant milestone
2. **Document decisions** when choosing between approaches
3. **Note blocking issues** so the next session knows where to resume
4. **Reference commits** for traceability
5. **Keep it concise** - another AI should be able to scan this in seconds and understand project state
