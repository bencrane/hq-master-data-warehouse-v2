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

### Phase 5: Company Endpoints (Done)

```
GET /api/companies
```
- Source: `core.companies_full` view
- Filters: industry, employee_range, city, state, country, domain, name

```
GET /api/companies/search?q={query}
```
- Source: `core.companies_full` view
- Searches by name OR domain (for autocomplete)

```
GET /api/companies/lookup?name={company_name}
```
- Source: `core.companies_full` view
- Returns domain for a given company name
- Response: `{ "found": true, "domain": "example.com", "name": "Example Inc", "match_type": "exact" }`
- Match types: `exact` (case-insensitive exact match), `partial` (contains match)

```
GET /api/companies/{domain}
```
- Source: `core.companies_full` view + `core.company_descriptions`
- Returns single company with full details including description and lead count

### Phase 6: Auth Endpoints (Done)

```
POST /api/auth/send-magic-link
```
- Sends magic link email for passwordless login
- Body: `{ "email": "user@example.com" }`

```
GET /api/auth/verify-magic-link?token={token}
```
- Verifies magic link token and creates session
- Returns session token and user info

```
GET /api/auth/session
```
- Validates session token from Authorization header
- Returns: `{ "valid": true, "user_id": "...", "expires_at": "..." }`

```
GET /api/auth/me
```
- Returns current user with org info
- Requires valid session token

```
GET /api/auth/orgs
```
- Lists all organizations

```
GET /api/auth/orgs/{slug}
```
- Get organization by slug

### Phase 7: Target Views Endpoints (Done)

```
GET /api/target-views
POST /api/target-views
GET /api/target-views/{id}
```
- CRUD for saved filter views

### Phase 8: Deploy to Railway (Done)

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
│   ├── filters.py       # /api/filters endpoints
│   ├── companies.py     # /api/companies endpoints
│   ├── auth.py          # /api/auth endpoints
│   └── views.py         # /api/target-views endpoints
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
| Phase 3: Compound endpoints | In Progress |
| Phase 4: Filter endpoints | Done |
| Phase 5: Company endpoints | Done |
| Phase 6: Auth endpoints | Done |
| Phase 7: Target views endpoints | Done |
| Phase 8: Railway deploy | Done |

---

## Next Steps

1. Add auth middleware to protect endpoints
2. Implement per-org data isolation
3. Add RBAC enforcement
