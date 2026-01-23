# New Modal Ingest Endpoint Checklist

Standard steps for creating a new Modal ingest function.

## Documentation Style

When documenting payload examples, use empty `{}` for nested objects:
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example/",
  "workflow_slug": "workflow-slug-here",
  "raw_person_payload": {},
  "raw_person_parsed_location_payload": {}
}
```
Do NOT unfurl/expand the full nested payload contents in examples.

## 1. Create Migration

Create SQL migration in `supabase/migrations/` with:
- `raw.<table_name>` - stores incoming payloads
- `extracted.<table_name>` - flattened/normalized data
- Appropriate indexes

## 2. Create Extraction Function

Add to `src/extraction/<module>.py`:
- Function that takes supabase client, raw_payload_id, and payload data
- Extracts/flattens fields to extracted table
- Returns extracted record ID

## 3. Create Ingest Function

Add to `src/ingest/<module>.py`:
- Pydantic request model for payload validation
- Function decorated with `@app.function()` and `@modal.fastapi_endpoint(method="POST")`
- Looks up workflow from registry
- Stores to raw table
- Calls extraction function

---

### CORRECT WAY (function in separate module)

**File: `src/ingest/person.py`**
```python
import os
import modal
from pydantic import BaseModel
from config import app, image
from extraction.person import extract_my_function

class MyRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_my_function(request: MyRequest) -> dict:
    from supabase import create_client
    # ... function body
```

**File: `src/app.py`**
```python
from ingest.person import ingest_my_function  # Import only
```

---

### INCORRECT WAY (function inline in app.py) - DO NOT DO THIS

**File: `src/app.py`**
```python
# WRONG - function defined directly in app.py
@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_my_function(data: dict) -> dict:  # WRONG - inline definition
    # This will NOT receive secrets properly
    pass
```

---

**WHY THIS MATTERS:** Modal handles secrets injection differently for imported module functions vs inline definitions. Inline functions in `app.py` fail silently when accessing `os.environ` for secrets.

## 4. Update app.py

In `src/app.py`:
- Add import for new ingest function
- Add to `__all__` list

## 5. Add Workflow to Registry

Insert into `reference.enrichment_workflow_registry`:
```sql
INSERT INTO reference.enrichment_workflow_registry 
(workflow_slug, provider, platform, payload_type, entity_type, description) 
VALUES (
  'your-workflow-slug',
  'provider',      -- e.g., 'clay'
  'platform',      -- e.g., 'clay'
  'payload_type',  -- e.g., 'discovery', 'enrichment', 'signal'
  'entity_type',   -- e.g., 'person', 'company'
  'Description of what this workflow does'
);
```

## 6. Apply Migration

Use Supabase MCP or dashboard to apply the migration.

## 7. Deploy

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

**IMPORTANT:** Always use `uv run` to ensure dependencies are available.

## Naming Constraints

**DNS Label Limit:** Function names must result in URLs under 63 characters for the hostname portion.

Format: `bencrane--hq-master-data-ingest-<function-name>.modal.run`

The prefix `bencrane--hq-master-data-ingest-` is 32 characters, leaving ~30 characters for the function name (with hyphens).

If names are too long, abbreviate: `people` → `ppl`, `location` → `lctn`, `parsed` → `prsd`
