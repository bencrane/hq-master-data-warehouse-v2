# HQ Master Data API - Architecture Plan

## Overview

FastAPI application deployed on Railway, serving as a thin routing layer over PostgreSQL (Supabase).

## Architecture

```
Frontend (Next.js, etc.)
        │
        ▼ HTTP
FastAPI on Railway
  • HTTP routing, auth, validation
  • Calls database views/functions
  • Shapes responses, generates OpenAPI docs
        │
        ▼ supabase.rpc() / .from_()
PostgreSQL (Supabase)
  • Views for simple queries
  • Functions for complex queries
  • All business logic lives here
```

## Design Principles

1. **Database-first logic** - Complex queries live in PostgreSQL functions, not application code
2. **Thin API layer** - FastAPI handles routing, validation, auth; not business logic
3. **Views for simple, Functions for complex** - Use views when filtering is enough; use functions for joins, multi-step logic, aggregations

## Query Type Patterns

| Query Type | PostgreSQL Approach | API Call Pattern |
|------------|---------------------|------------------|
| Simple reads with filters | Views | `supabase.from_("view").select()` |
| Complex joins, multi-step | Functions | `supabase.rpc("fn_name", params)` |
| Aggregations, analytics | Functions | `supabase.rpc()` |
| Write operations | Functions | `supabase.rpc()` |

---

## Endpoints

### Phase 1: Core Leads (Done)

```
GET /api/leads
```
- Source: `core.leads` view
- Filters: job_function, seniority, industry, employee_range, location fields, job_start_date

### Phase 2: Signal Endpoints (Done)

```
GET /api/leads/new-in-role
```
- Source: `core.leads` view with job_start_date filter
- Additional param: `started_within_days` (default 90)

```
GET /api/leads/recently-promoted
```
- Source: `core.leads_recently_promoted` view
- Additional param: `promoted_within_days` (default 180)

```
GET /api/leads/at-vc-portfolio
```
- Source: `core.leads_at_vc_portfolio` view
- Additional param: `vc_name` (optional)

### Phase 3: Compound Endpoints (In Progress)

```
GET /api/leads/by-past-employer?domains=salesforce.com,hubspot.com
```
- Source: PostgreSQL function `core.get_leads_by_past_employer(domain_list)`
- Joins person_work_history with leads
- Status: Needs function implementation

### Phase 4: Filter Endpoints (Done)

```
GET /api/filters/job-functions
GET /api/filters/seniorities
GET /api/filters/industries
GET /api/filters/employee-ranges
GET /api/filters/vc-firms
GET /api/filters/person-countries
GET /api/filters/person-states
```

### Phase 5: Deploy to Railway (Not Started)

---

## Database Objects

### Views (Existing)

| View | Schema | Purpose |
|------|--------|---------|
| `leads` | core | Primary leads view - people + companies joined |
| `leads_recently_promoted` | core | Leads with promotion data |
| `leads_at_vc_portfolio` | core | Leads at VC portfolio companies |
| `companies_full` | core | Enriched company view |
| `people_full` | core | Enriched people view |

### Functions (To Create)

| Function | Purpose |
|----------|---------|
| `core.get_leads_by_past_employer(domain_list TEXT[])` | Find leads who worked at specified companies |

---

## File Structure

```
hq-api/
├── main.py              # FastAPI app, CORS, routers
├── db.py                # Supabase connection, schema helpers
├── models.py            # Pydantic response models
├── routers/
│   ├── leads.py         # /api/leads endpoints
│   └── filters.py       # /api/filters endpoints
├── requirements.txt
├── railway.toml         # Railway deploy config
├── .env                 # Credentials (not committed)
├── .env.example
└── API_PLAN.md          # This file
```

---

## Response Format

All list endpoints return:

```json
{
  "data": [...],
  "meta": {
    "total": 12345,
    "limit": 50,
    "offset": 0
  }
}
```

---

## Current Status

| Phase | Status |
|-------|--------|
| Phase 1: Core leads endpoint | Done |
| Phase 2: Signal endpoints | Done |
| Phase 3: Compound endpoints | In Progress - needs PostgreSQL function |
| Phase 4: Filter endpoints | Done |
| Phase 5: Railway deploy | Not Started |

---

## Next Steps

1. Create `core.get_leads_by_past_employer()` PostgreSQL function
2. Update `/api/leads/by-past-employer` to use the function
3. Test all endpoints
4. Deploy to Railway
5. Document API for frontend developers
