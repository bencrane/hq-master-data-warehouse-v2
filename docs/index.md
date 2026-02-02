# HQ Master Data Warehouse - Documentation Index

Central documentation hub for the HQ lead intelligence platform.

---

## Quick Start

| I want to... | Go to |
|--------------|-------|
| Understand current work | [Workbench README](./workbench/README.md) |
| See all pending tasks | [TODO.md](./workbench/TODO.md) |
| Understand the architecture | [Architecture Overview](./architecture/overview.md) |
| Create a new Modal workflow | [Workflow Development Guide](./workflows/development-guide.md) |
| Add a new API endpoint | [API Endpoint Protocol](./api/endpoints.md) |

---

## Documentation Structure

```
docs/
├── CLAUDE.md              # Quick context for Claude Code sessions
├── index.md               # This file
│
├── architecture/          # How the system works (stable reference)
│   ├── overview.md        # System architecture diagram
│   ├── api-principles.md  # FastAPI design principles
│   ├── frontend-principles.md
│   └── data-ingestion.md  # 4-schema data flow
│
├── api/                   # API documentation
│   ├── endpoints.md       # Endpoint protocol
│   ├── pricing-enrichment.md
│   └── external-api-reference/  # Third-party API docs
│
├── workflows/             # Modal data pipelines
│   ├── README.md          # Workflow overview
│   ├── development-guide.md
│   ├── endpoint-checklist.md
│   └── catalog/           # Individual workflow docs
│
├── operations/            # Deployment & infrastructure
│   └── mcp/              # MCP server configurations
│
├── data-mapping/          # Data schema documentation
│
├── planning/              # Future plans and proposals
│
├── postmortems/           # Incident documentation
│
└── workbench/             # ACTIVE WORK (check here first)
    ├── README.md          # Current session priorities
    ├── TODO.md            # Master task list
    ├── active/            # Work in progress
    └── backlog/           # Queued items
```

---

## Key Principles

1. **Database owns business logic** - All joins/filters in PostgreSQL
2. **Thin API layer** - FastAPI endpoints < 20 lines
3. **4-schema data flow** - raw -> extracted -> reference -> core
4. **Single source of truth** - `core.leads` is the canonical view

---

## Code Locations

| Component | Path |
|-----------|------|
| FastAPI Backend | `/hq-api/` |
| Next.js Frontend | `/frontend/` |
| Modal Functions | `/modal-functions/` |
| Database Migrations | `/supabase/migrations/` |

---

## External Links

- [Railway Dashboard](https://railway.app) - API deployment
- [Supabase Dashboard](https://supabase.com/dashboard) - Database
- [Modal Dashboard](https://modal.com) - Serverless functions
