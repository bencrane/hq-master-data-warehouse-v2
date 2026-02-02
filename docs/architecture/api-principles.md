# HQ API Architecture Principles

This document defines the non-negotiable principles for building and maintaining the HQ Master Data API. All contributors must follow these principles to ensure consistency, maintainability, and scalability.

---

## Principle 1: Database Owns Business Logic

**All business logic lives in PostgreSQL. The API layer does not contain business logic.**

### What belongs in PostgreSQL:
- Joins between tables
- Filtering logic beyond simple equality
- Aggregations and calculations
- Data transformations
- Multi-step queries
- Scoring or ranking logic

### What belongs in FastAPI:
- HTTP routing
- Request validation (Pydantic)
- Authentication/authorization
- Rate limiting
- Response shaping
- Error handling
- OpenAPI documentation

### Example - CORRECT:
```python
# FastAPI just calls the function
result = supabase.rpc("get_leads_by_past_employer", {"domains": domain_list})
```

### Example - WRONG:
```python
# DO NOT put join logic in Python
work_history = supabase.from_("work_history").select("linkedin_url").execute()
urls = [r["linkedin_url"] for r in work_history.data]
leads = supabase.from_("leads").in_("linkedin_url", urls).execute()
```

---

## Principle 2: Views for Simple, Functions for Complex

**Use the simplest PostgreSQL object that solves the problem.**

| Complexity | PostgreSQL Object | When to Use |
|------------|-------------------|-------------|
| Single table with filters | Direct table query | Rare - prefer views |
| Joined data, standard filters | **View** | Most common case |
| Multi-step logic, parameters | **Function** | Complex queries |
| Write operations with validation | **Function** | All writes |

### Decision Tree:
```
Does the query need parameters beyond filters?
  └── Yes → Function
  └── No → Can it be expressed as a single SELECT?
              └── Yes → View
              └── No → Function
```

---

## Principle 3: Thin API Layer

**FastAPI endpoints should be short and consistent. If an endpoint has more than ~20 lines of logic, it's doing too much.**

### Database Connection Strategy:

| Query Type | Connection Method | Why |
|------------|-------------------|-----|
| Simple table queries | Supabase client | Convenience, fine for basic CRUD |
| PostgreSQL functions | **asyncpg (direct)** | Full timeout control, no PostgREST limitations |
| Views with filters | Either | Depends on complexity |

**Use direct PostgreSQL connections (asyncpg) for calling functions.** PostgREST has timeout constraints that cannot be overridden at the function level.

### Standard endpoint structure:
```python
@router.get("/endpoint")
async def get_something(
    param1: str = Query(...),
    param2: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Docstring describing the endpoint."""

    # 1. Call database function via asyncpg
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM core.function_name($1, $2, $3)",
        param1, limit, offset
    )

    # 2. Return shaped response
    return Response(data=[dict(r) for r in rows], meta=Meta(...))
```

### What is NOT allowed in endpoints:
- Loops that process data
- Multiple sequential database calls that depend on each other
- Business logic conditionals
- Data transformations beyond basic response shaping

---

## Principle 4: Explicit Column Selection

**Never use SELECT * in production code.**

### Why:
- Prevents schema changes from breaking the API
- Makes data contracts explicit
- Avoids serialization issues with Supabase
- Documents exactly what data is returned

### Implementation:
```python
# Define columns at module level
LEAD_COLUMNS = ",".join([
    "person_id", "linkedin_url", "full_name", ...
])

# Use in queries
result = supabase.from_("leads").select(LEAD_COLUMNS).execute()
```

---

## Principle 5: Consistent Response Shapes

**All list endpoints return the same structure.**

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

**All single-item endpoints return the object directly.**

```json
{
  "id": "uuid",
  "field": "value"
}
```

**All errors return:**

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message"
  }
}
```

---

## Principle 6: PostgreSQL Functions Are Typed

**All PostgreSQL functions must have explicit input and output types.**

### Template:
```sql
CREATE OR REPLACE FUNCTION core.function_name(
    param1 TEXT,
    param2 TEXT[] DEFAULT NULL,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    column1 UUID,
    column2 TEXT,
    ...
)
LANGUAGE sql
STABLE  -- or VOLATILE for writes
AS $$
    SELECT ...
$$;
```

### Naming conventions:
- Functions in `core` schema
- Prefix with action: `get_`, `find_`, `count_`, `create_`, `update_`
- Snake_case names
- Parameters prefixed with `p_` if they shadow column names

---

## Principle 7: No Workarounds

**If something doesn't fit the pattern, fix the pattern or create the right database object. Do not create workarounds.**

### Signs of a workaround:
- "Limit to 500 to prevent overflow"
- Multiple database round-trips
- Processing data in Python loops
- Try/except around query logic
- Comments explaining why something is hacky

### Correct response to hitting a limitation:
1. Stop
2. Identify the correct PostgreSQL object (view or function)
3. Create it
4. Use it from the API

---

## Principle 8: Single Source of Truth

**Each piece of data has one authoritative source.**

| Data | Source |
|------|--------|
| Leads (people + companies) | `core.leads` view |
| People who worked at X | `core.get_leads_by_past_employer()` function |
| Filter dropdown values | `core.leads` distinct queries |
| VC portfolio leads | `core.leads_at_vc_portfolio` view |

**The API does not create alternative sources. It exposes the canonical sources.**

---

## Principle 9: Documentation Lives With Code

**Every PostgreSQL function and view must have a comment. Every endpoint must have a docstring.**

### PostgreSQL:
```sql
COMMENT ON FUNCTION core.get_leads_by_past_employer IS
'Returns leads who previously worked at any of the specified company domains.';
```

### FastAPI:
```python
@router.get("/by-past-employer")
async def get_leads_by_past_employer(...):
    """
    Get leads who previously worked at specified companies.

    Finds people in work history who worked at any of the provided
    company domains, then returns their current lead information.
    """
```

---

## Checklist for New Endpoints

Before adding a new endpoint, verify:

- [ ] Does the data source exist as a view or function?
- [ ] If not, have I created the appropriate PostgreSQL object?
- [ ] Is my endpoint under 20 lines of logic?
- [ ] Am I using explicit column selection?
- [ ] Does my response match the standard shape?
- [ ] Is there a docstring?
- [ ] Am I calling the database exactly once (or zero times for cached data)?

---

## Enforcement

These principles are enforced through:
1. Code review
2. This document as the reference
3. Refactoring any code that violates principles before adding features

**When in doubt, move logic to PostgreSQL.**
