# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Data Sources                               │
│    Clay Webhooks  ·  Apollo API  ·  LinkedIn SalesNav  ·  Manual    │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Modal Serverless Functions                        │
│                     /modal-functions/src/ingest/                     │
│                                                                      │
│   • Receive webhooks from Clay                                       │
│   • Write to raw schema (unmodified payloads)                       │
│   • Extract to extracted schema (flattened rows)                    │
│   • Some workflows coalesce to core schema                          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PostgreSQL (Supabase)                            │
│                                                                      │
│   ┌─────────┐   ┌────────────┐   ┌───────────┐   ┌──────────┐      │
│   │   raw   │ → │ extracted  │ → │ reference │ → │   core   │      │
│   │         │   │            │   │           │   │          │      │
│   │ JSON    │   │ Flattened  │   │ Lookups   │   │Normalized│      │
│   │ blobs   │   │ rows       │   │ catalogs  │   │ entities │      │
│   └─────────┘   └────────────┘   └───────────┘   └──────────┘      │
│                                                                      │
│   Views: core.leads, core.leads_recently_promoted, etc.             │
│   Functions: core.get_leads_by_past_employer(), etc.                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI (hq-api)                                │
│                      Hosted on Railway                               │
│                                                                      │
│   • Thin layer - no business logic                                  │
│   • Calls views/functions, returns JSON                             │
│   • Auth via magic links                                            │
│   • ~39 endpoints                                                   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                                 │
│                      /frontend/                                      │
│                                                                      │
│   • React 19 + TypeScript                                           │
│   • Tailwind CSS 4 + shadcn/ui                                      │
│   • Server components + Server actions                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Schema Layers

| Schema | Purpose | Retention | Example |
|--------|---------|-----------|---------|
| `raw` | Unmodified JSON payloads | Permanent | `raw.claygent_discovery_raw` |
| `extracted` | Flattened, one row per entity | Permanent | `extracted.person_experience` |
| `reference` | Auto-populated lookup catalogs | Permanent | `reference.job_functions` |
| `core` | Normalized, query-optimized | Permanent | `core.leads`, `core.companies_full` |

---

## Key Design Decisions

### 1. Database Owns Business Logic
All joins, filters, aggregations, and transformations happen in PostgreSQL views and functions. The API layer is deliberately thin.

**Rationale:** Single source of truth, easier to test, no logic duplication between API and database.

### 2. Views for Simple, Functions for Complex
- **Views:** Pre-joined data with standard filters (most common)
- **Functions:** Parameterized queries, multi-step logic, write operations

### 3. Four-Schema Data Flow
Raw -> Extracted -> Reference -> Core ensures:
- Original data preserved (audit trail)
- Each layer serves a specific purpose
- Core schema is always query-optimized

### 4. Explicit Column Selection
Never `SELECT *`. All queries explicitly list columns to prevent schema drift breaking the API.

---

## Related Documents

- [API Principles](./api-principles.md) - Detailed API architecture principles
- [Frontend Principles](./frontend-principles.md) - UI/UX design system
- [Data Ingestion Protocol](./data-ingestion.md) - Schema layer patterns
