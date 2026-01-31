# API Endpoint Protocol (Frontend-Facing Endpoints)

## CRITICAL: Read This Before Creating Any Endpoint That The Frontend Will Call

This document defines the MANDATORY protocol for creating API endpoints **that the frontend will call**.

This does NOT apply to:
- Clay webhook endpoints (those go directly to Modal)
- Internal batch processing endpoints
- Admin-only backend operations

This DOES apply to:
- Any endpoint the Next.js frontend needs to fetch data from
- Any endpoint that powers a UI component
- Any endpoint that a user action triggers

Follow this exactly every time.

---

## Architecture Overview

```
Frontend (Next.js)
      ↓
Railway API (api.revenueinfra.com)  ← Frontend calls THIS
      ↓
Modal Functions (serverless compute) ← Railway wraps these
      ↓
Supabase (database)
```

**RULE: The frontend NEVER calls Modal endpoints directly.**

---

## When Creating a New Feature That Needs an API

### Step 1: Create the Modal Function (if needed)

Location: `modal-functions/src/ingest/`

```python
# modal-functions/src/ingest/my_new_function.py

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def my_new_function(request: MyRequest) -> dict:
    # ... implementation
```

**Then:**
- Add import to `modal-functions/src/app.py`
- Deploy: `cd modal-functions && uv run python -m modal deploy src/app.py`

### Step 2: Create the Railway API Wrapper (MANDATORY)

Location: `hq-api/routers/`

The Railway API wrapper goes in the appropriate router file:
- `companies.py` - company-related endpoints
- `leads.py` - leads/people endpoints
- `views.py` - saved views, filters
- `filters.py` - filter options/metadata

```python
# hq-api/routers/companies.py

@router.get("/{domain}/my-feature")
async def get_my_feature(domain: str):
    """
    Description of what this does.
    """
    # Query database directly OR call Modal function
    result = core().from_("table").select("*").eq("domain", domain).execute()

    return {
        "success": True,
        "data": result.data
    }
```

### Step 3: Commit and Deploy

```bash
# Commit both Modal and Railway changes
git add -A
git commit -m "feat: add my-feature endpoint"
git push origin main
```

Railway auto-deploys from GitHub.

### Step 4: Update Frontend to Use Railway URL

Frontend should call:
```
https://api.revenueinfra.com/api/companies/{domain}/my-feature
```

NOT:
```
https://bencrane--hq-master-data-ingest-my-function.modal.run  # WRONG
```

---

## Directory Structure Reference

```
hq-master-data-warehouse-v2/
├── hq-api/                    # Railway API (what frontend calls)
│   ├── routers/
│   │   ├── companies.py       # /api/companies/* endpoints
│   │   ├── leads.py           # /api/leads/* endpoints
│   │   ├── views.py           # /api/views/* endpoints
│   │   └── filters.py         # /api/filters/* endpoints
│   ├── main.py
│   └── db.py
│
├── modal-functions/           # Modal serverless functions
│   └── src/
│       ├── app.py             # Main entry point (imports all)
│       ├── ingest/            # Ingestion endpoints (from Clay, etc.)
│       └── extraction/        # Data extraction logic
│
└── supabase/
    └── migrations/            # Database migrations
```

---

## Endpoint Naming Conventions

### Railway API (what frontend uses)
```
GET  /api/companies/{domain}              # Get single company
GET  /api/companies/{domain}/customers    # Get company's customers
GET  /api/companies/{domain}/icp          # Get company's ICP criteria
POST /api/leads                           # Create/query leads
GET  /api/views/{slug}                    # Get saved view
```

### Modal Functions (internal use only)
```
ingest_*          # Data ingestion from external sources
lookup_*          # Data retrieval/lookup
upsert_*          # Data upsert operations
extract_*         # Data extraction/transformation
```

---

## Checklist For Every New Endpoint

- [ ] Modal function created (if needed for compute-heavy work)
- [ ] Modal function added to `app.py` imports
- [ ] Modal function deployed (`uv run python -m modal deploy src/app.py`)
- [ ] Railway API wrapper created in appropriate router
- [ ] Railway changes committed and pushed
- [ ] Frontend uses Railway URL, not Modal URL
- [ ] Endpoint documented (OpenAPI auto-generates from FastAPI)

---

## Common Mistakes to Avoid

### ❌ WRONG: Frontend calling Modal directly
```javascript
// BAD - brittle, exposes implementation
fetch('https://bencrane--hq-master-data-ingest-lookup-company-icp.modal.run', {
  method: 'POST',
  body: JSON.stringify({ domain: 'example.com' })
})
```

### ✅ CORRECT: Frontend calling Railway API
```javascript
// GOOD - stable, abstracted
fetch('https://api.revenueinfra.com/api/companies/example.com/icp')
```

### ❌ WRONG: Creating Modal endpoint without Railway wrapper
"I'll just use the Modal URL for now and add Railway later"
→ NO. Always create both at the same time.

### ❌ WRONG: Putting env vars for Modal URLs in frontend
```
MODAL_ICP_ENDPOINT=https://bencrane--...
```
→ NO. Frontend only needs `API_BASE_URL=https://api.revenueinfra.com`

---

## When Modal Functions Are Needed vs Direct DB Queries

### Use Modal Functions For:
- Heavy compute (AI/ML processing)
- External API calls (OpenAI, Clay webhooks)
- Long-running operations
- Operations needing specific Python packages

### Use Direct DB Queries (in Railway) For:
- Simple CRUD operations
- Data lookups/retrieval
- Filtering/pagination
- Anything the Supabase client can do directly

---

## Example: Complete Flow for New Feature

**Scenario:** Add endpoint to get similar companies for a domain

### 1. Check if Modal function exists
```bash
grep -r "similar_companies" modal-functions/src/
```

### 2. Modal function exists, create Railway wrapper

```python
# hq-api/routers/companies.py

@router.get("/{domain}/similar")
async def get_similar_companies(domain: str, limit: int = Query(25, le=100)):
    """Get similar companies for a domain."""
    result = (
        extracted()
        .from_("company_enrich_similar")
        .select("company_name, company_domain, similarity_score")
        .eq("input_domain", domain)
        .order("similarity_score", desc=True)
        .limit(limit)
        .execute()
    )

    return {
        "success": True,
        "domain": domain,
        "similar_companies": result.data
    }
```

### 3. Commit and push
```bash
git add hq-api/routers/companies.py
git commit -m "feat: add /api/companies/{domain}/similar endpoint"
git push origin main
```

### 4. Frontend uses
```javascript
const response = await fetch(`${API_BASE_URL}/api/companies/${domain}/similar`)
```

---

## Final Note

If you're unsure whether to create a Railway wrapper: **CREATE IT**.

The extra 5 minutes now saves hours of debugging "why isn't the frontend working" later.
