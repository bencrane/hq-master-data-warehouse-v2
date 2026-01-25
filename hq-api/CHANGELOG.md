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
