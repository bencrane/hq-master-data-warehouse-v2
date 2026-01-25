# HQ Master Data API - Project Plan

## Project Overview

**Objective:** Build a production-ready API layer for the HQ canonical database that enables multiple frontends to query leads, companies, and people data.

**Stack:** FastAPI + Railway + PostgreSQL (Supabase)

**Governing Document:** `ARCHITECTURE_PRINCIPLES.md`

---

## Stage 1: Foundation

**Goal:** Establish core infrastructure and primary endpoint.

### Project 1.1: Database Views
Create the foundational views that power the API.

| Task | Status | Notes |
|------|--------|-------|
| 1.1.1 Verify `core.leads` view exists and is correct | Done | Primary leads view |
| 1.1.2 Create `core.leads_recently_promoted` view | Done | Joins leads with promotions |
| 1.1.3 Create `core.leads_at_vc_portfolio` view | Done | Joins leads with VC portfolio |

### Project 1.2: FastAPI Scaffolding
Set up the API application structure.

| Task | Status | Notes |
|------|--------|-------|
| 1.2.1 Create project directory structure | Done | hq-api/ |
| 1.2.2 Create `main.py` with CORS, routers | Done | |
| 1.2.3 Create `db.py` with schema helpers | Done | core(), raw(), extracted() |
| 1.2.4 Create `models.py` with Pydantic models | Done | Lead, Meta, Response models |
| 1.2.5 Create `requirements.txt` | Done | |
| 1.2.6 Create `.env.example` | Done | |
| 1.2.7 Create `railway.toml` | Done | |

### Project 1.3: Core Leads Endpoint
Build the primary `/api/leads` endpoint.

| Task | Status | Notes |
|------|--------|-------|
| 1.3.1 Define LEAD_COLUMNS constant | Done | Explicit column selection |
| 1.3.2 Implement `apply_lead_filters()` helper | Done | Reusable filter logic |
| 1.3.3 Implement `GET /api/leads` | Done | With all filters |
| 1.3.4 Test endpoint locally | Done | 1.3M leads returned |

**Stage 1 Status: Complete**

---

## Stage 2: Signal Endpoints

**Goal:** Add endpoints for time-based lead signals (new in role, recently promoted).

### Project 2.1: New-in-Role Endpoint

| Task | Status | Notes |
|------|--------|-------|
| 2.1.1 Implement `GET /api/leads/new-in-role` | Done | Uses job_start_date filter |
| 2.1.2 Add `started_within_days` parameter | Done | Default 90 |
| 2.1.3 Test endpoint | Done | 143K leads in last 180 days |

### Project 2.2: Recently Promoted Endpoint

| Task | Status | Notes |
|------|--------|-------|
| 2.2.1 Define LEAD_PROMOTED_COLUMNS constant | Done | |
| 2.2.2 Implement `GET /api/leads/recently-promoted` | Done | Uses leads_recently_promoted view |
| 2.2.3 Add `promoted_within_days` parameter | Done | Default 180 |
| 2.2.4 Test endpoint | Done | |

### Project 2.3: VC Portfolio Endpoint

| Task | Status | Notes |
|------|--------|-------|
| 2.3.1 Define LEAD_VC_COLUMNS constant | Done | |
| 2.3.2 Implement `GET /api/leads/at-vc-portfolio` | Done | Uses leads_at_vc_portfolio view |
| 2.3.3 Add `vc_name` filter parameter | Done | Optional |
| 2.3.4 Test endpoint | Done | 1.5M leads |

**Stage 2 Status: Complete**

---

## Stage 3: Filter Endpoints

**Goal:** Provide dropdown values for frontend filter UIs.

### Project 3.1: Filter Endpoints

| Task | Status | Notes |
|------|--------|-------|
| 3.1.1 Implement `GET /api/filters/job-functions` | Done | |
| 3.1.2 Implement `GET /api/filters/seniorities` | Done | |
| 3.1.3 Implement `GET /api/filters/industries` | Done | |
| 3.1.4 Implement `GET /api/filters/employee-ranges` | Done | Sorted numerically |
| 3.1.5 Implement `GET /api/filters/vc-firms` | Done | From raw.vc_firms |
| 3.1.6 Implement `GET /api/filters/person-countries` | Done | |
| 3.1.7 Implement `GET /api/filters/person-states` | Done | |
| 3.1.8 Test all filter endpoints | Done | |

**Stage 3 Status: Complete**

---

## Stage 4: Compound Query Endpoints

**Goal:** Add endpoints requiring PostgreSQL functions (complex joins, multi-step logic).

### Project 4.1: By-Past-Employer Function

| Task | Status | Notes |
|------|--------|-------|
| 4.1.1 Design function signature | Not Started | Input: domain_list, filters, limit, offset |
| 4.1.2 Create `core.get_leads_by_past_employer()` function | Not Started | SQL function |
| 4.1.3 Add COMMENT to function | Not Started | Per principles |
| 4.1.4 Test function directly in SQL | Not Started | |

### Project 4.2: By-Past-Employer Endpoint

| Task | Status | Notes |
|------|--------|-------|
| 4.2.1 Refactor `GET /api/leads/by-past-employer` to use function | Not Started | Replace workaround |
| 4.2.2 Test endpoint | Not Started | |
| 4.2.3 Verify no URL length issues | Not Started | |

**Stage 4 Status: Not Started**

---

## Stage 5: Deployment

**Goal:** Deploy API to Railway for production use.

### Project 5.1: Railway Setup

| Task | Status | Notes |
|------|--------|-------|
| 5.1.1 Create Railway project | Not Started | |
| 5.1.2 Configure environment variables | Not Started | SUPABASE_URL, SUPABASE_SERVICE_KEY |
| 5.1.3 Connect GitHub repo | Not Started | Auto-deploy on push |
| 5.1.4 Deploy application | Not Started | |
| 5.1.5 Verify health endpoint | Not Started | /health |

### Project 5.2: Production Verification

| Task | Status | Notes |
|------|--------|-------|
| 5.2.1 Test all endpoints on production URL | Not Started | |
| 5.2.2 Verify CORS works from test frontend | Not Started | |
| 5.2.3 Document production URL | Not Started | |

**Stage 5 Status: Not Started**

---

## Stage 6: Documentation & Handoff

**Goal:** Complete documentation for frontend developers.

### Project 6.1: API Documentation

| Task | Status | Notes |
|------|--------|-------|
| 6.1.1 Verify OpenAPI docs at /docs | Done | Auto-generated |
| 6.1.2 Write API_REFERENCE.md for frontend devs | Not Started | |
| 6.1.3 Include example requests/responses | Not Started | |
| 6.1.4 Document error codes | Not Started | |

### Project 6.2: Architecture Documentation

| Task | Status | Notes |
|------|--------|-------|
| 6.2.1 Create ARCHITECTURE_PRINCIPLES.md | Done | |
| 6.2.2 Create API_PLAN.md | Done | |
| 6.2.3 Create PROJECT_PLAN.md | Done | This document |

**Stage 6 Status: In Progress**

---

## Summary

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 1 | Foundation | Complete |
| Stage 2 | Signal Endpoints | Complete |
| Stage 3 | Filter Endpoints | Complete |
| Stage 4 | Compound Query Endpoints | Not Started |
| Stage 5 | Deployment | Not Started |
| Stage 6 | Documentation & Handoff | In Progress |

---

## Current Focus

**Next Action:** Stage 4, Project 4.1, Task 4.1.1 - Design function signature for `get_leads_by_past_employer`

---

## Dependencies

```
Stage 1 ─┬─► Stage 2 ─┬─► Stage 4 ───► Stage 5
         │            │
         └─► Stage 3 ─┘
                      │
         Stage 6 ◄────┘ (parallel)
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Supabase URL length limits | Use PostgreSQL functions for complex queries |
| Schema changes break API | Explicit column selection, typed models |
| Inconsistent endpoint behavior | Architecture principles document, code review |
| Railway deployment issues | Health endpoint, staged rollout |
