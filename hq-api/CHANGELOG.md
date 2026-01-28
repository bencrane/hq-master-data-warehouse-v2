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

## 2026-01-28

### Update 003: Lead Data Quality Backfill - 80% Increase in Visible Leads

**What was done:**

1. **Created intermediary table for job title backfill:**
   - `core.persons_missing_cleaned_title` - staging table for 355,081 people missing cleaned job titles
   - Used direct PostgreSQL connection (not Supabase client) to avoid statement timeout issues

2. **Backfilled job_function for leads:**
   - Started at 66% coverage
   - Applied pattern matching against raw job titles using ILIKE
   - Patterns: Engineering (engineer, developer, SDE), Sales (sales, account executive, SDR, BDR), Marketing (marketing, growth, demand gen), etc.
   - Added "Executive Leadership" to `reference.job_functions` for C-suite/Founder roles (not "General")
   - Final coverage: **96.5%**

3. **Backfilled seniority for leads:**
   - Started at 61% coverage (773,953 leads with seniority)
   - Applied pattern matching: C-Suite → C-Level, VP/Vice President → VP, Head of → Head, Director → Director, Manager → Manager, Senior → Senior, Entry/Junior/Associate → Entry Level, Owner/Partner/Principal → Owner
   - Added "Individual Contributor" to `reference.seniorities`
   - Final coverage: **98.4%**

4. **Cleaned non-B2B and low-quality records:**
   - Deleted records with non-B2B job titles (barista, dog walker, delivery driver, model, actress, trainee, retired, etc.)
   - Deleted records with foreign language job titles
   - Deleted records for people in non-English-speaking countries (kept: US, Canada, UK, Australia, Ireland, Germany, Netherlands, New Zealand, Singapore, India, Philippines, South Africa)

**Key result:**
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Visible leads in dashboard | ~501,000 | **902,364** | **+80%** |
| Job function coverage | 66% | 96.5% | +30.5% |
| Seniority coverage | 61% | 98.4% | +37.4% |

**Key decisions:**

1. **Pattern matching approach over ML:**
   - Simple ILIKE patterns were sufficient for high coverage
   - Patterns are transparent and easily adjusted
   - No external dependencies or model management

2. **Delete low-quality records rather than tag:**
   - Non-B2B roles (retail, hospitality, gig economy) are not useful for sales
   - Foreign language titles indicate non-target market
   - Non-English-speaking countries outside ICP
   - Cleaner data > larger numbers

3. **"Executive Leadership" vs "General" for C-suite:**
   - User correction: Founders, CEOs, Chiefs should be "Executive Leadership" not "General"
   - Added to `reference.job_functions` with sort_order 0 (top priority)

4. **Individual Contributor as separate seniority:**
   - Not part of Clay taxonomy but useful for targeting ICs
   - NOT applied to vague single-word titles like "Marketing", "Sales" - those were deleted

**Files changed:**
```
reference.job_functions     - Added "Executive Leadership"
reference.seniorities       - Added "Individual Contributor"
core.person_job_titles      - Backfilled matched_job_function, matched_seniority
core.persons_missing_cleaned_title - Created as staging table
```

**SQL patterns used (for future reference):**
```sql
-- Job function pattern matching
UPDATE core.person_job_titles
SET matched_job_function = 'Engineering'
WHERE matched_job_function IS NULL
AND (matched_cleaned_job_title ILIKE '%engineer%'
  OR matched_cleaned_job_title ILIKE '%developer%');

-- Seniority pattern matching
UPDATE core.person_job_titles
SET matched_seniority = 'C-Level'
WHERE matched_seniority IS NULL
AND (matched_cleaned_job_title ILIKE '%chief %'
  OR matched_cleaned_job_title ILIKE 'ceo%'
  OR matched_cleaned_job_title ILIKE 'cfo%');

-- Delete non-B2B
DELETE FROM core.person_job_titles
WHERE matched_cleaned_job_title ILIKE ANY(ARRAY[
  '%barista%', '%dog walker%', '%retired%', '%model%'
]);

-- Delete non-English-speaking countries
DELETE FROM core.person_job_titles pjt
USING core.people_full pf
WHERE pjt.linkedin_url = pf.linkedin_url
  AND pjt.matched_job_function IS NULL
  AND pf.person_country NOT ILIKE '%united states%'
  AND pf.person_country NOT ILIKE '%canada%'
  -- ... other English-speaking countries
```

---

### Update 004: Star Schema Design for Company Data (In Progress)

**Context:**

The manual backfill work above took significant effort. The goal now is to **automate matching at ingest time** so that when Clay payloads arrive, they're automatically matched against lookup tables and written to normalized dimension tables.

**Design decision: Star Schema over Stripe-style single table**

Two approaches were considered:

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| Stripe-style | Single `core.companies` table with all fields and FKs to reference tables | Simple, single source of truth | Hard to track which source provided which field |
| **Star Schema** | Dimension table per field (names, locations, industries, etc.) with source attribution | Clear provenance, supports multiple sources, easy to coalesce with priority | More tables, more complex joins |

**Decision: Star Schema** - because:
- Data comes from multiple sources (Clay, Crunchbase, Apollo, LinkedIn)
- Different sources have different quality (Crunchbase names > Clay names)
- Need to track which source provided which value
- Frontend needs single coalesced view, but backend needs source attribution
- Same pattern will apply to people data

**Schema design:**

Each dimension table has:
- `domain` - company identifier
- `source` - data source (clay, crunchbase, apollo, etc.)
- `raw_*` columns - exactly what the source provided
- `matched_*` columns - normalized values from lookup tables
- Composite unique key: `(domain, source)`

**Reference tables created:**
```sql
reference.company_types       -- Public Company, Private Company, etc.
reference.funding_ranges      -- <$1M, $1M-$5M, ..., $1B+
reference.revenue_ranges      -- <$1M, $1M-$5M, ..., $100B+
reference.funding_range_lookup -- Maps Clay strings to our ranges
reference.revenue_range_lookup -- Maps Clay strings to our ranges
```

**Dimension tables created:**
```sql
core.company_names            -- domain, source, raw_name, cleaned_name, linkedin_url
core.company_employee_ranges  -- domain, source, raw_size, matched_employee_range
core.company_types            -- domain, source, raw_type, matched_type
core.company_locations        -- domain, source, raw_location, matched_city/state/country
core.company_industries       -- domain, source, raw_industry, matched_industry
core.company_funding          -- domain, source, raw_funding_range, matched_funding_range
core.company_revenue          -- domain, source, raw_revenue_range, matched_revenue_range
core.company_descriptions     -- domain, source, description, tagline
```

**Coalesced view:**
- `core.companies_full_v2` - joins all dimension tables
- Coalesces values with priority order (crunchbase > clay > apollo)
- Single row per company for frontend consumption

**Example Clay payload being handled:**
```json
{
  "name": "Google",
  "size": "10,001+ employees",
  "type": "Public Company",
  "domain": "google.com",
  "country": "United States",
  "industry": "Software Development",
  "location": "Mountain View, CA",
  "industries": ["Software Development"],
  "description": "...",
  "linkedin_url": "https://www.linkedin.com/company/google",
  "annual_revenue": "100B-1T",
  "total_funding_amount_range_usd": "$100M - $250M"
}
```

**Known issue - existing tables have different schemas:**

Tables `core.company_locations`, `core.company_industries`, `core.company_descriptions` already exist with:
- Unique constraint on `domain` only (not `domain, source`)
- Column names like `city` not `matched_city`
- Missing `raw_*` columns

**Next steps:**
1. Decide: modify existing tables or create new `_v2` tables
2. Backfill existing data from `extracted.company_discovery` into dimension tables
3. Update `modal-mcp-server/src/extraction/company.py` to write to dimension tables at ingest time
4. Apply same pattern to people data (find-clay-people payloads)

**Blocking question:**
Are the existing `core.company_*` tables actively used by frontend/API? If so, need migration strategy.

**Files created:**
```
supabase/migrations/20260128_company_star_schema.sql
```

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
