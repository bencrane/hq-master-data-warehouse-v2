# Modal Development Guide

**Last Updated:** 2026-01-24

How to create, modify, and deploy Modal endpoints for the HQ Master Data Ingest app.

---

## Table of Contents

1. [Creating a New Endpoint](#creating-a-new-endpoint)
2. [Code Patterns](#code-patterns)
3. [Deployment](#deployment)
4. [Naming Conventions](#naming-conventions)
5. [Common Pitfalls](#common-pitfalls)
6. [Testing](#testing)

---

## Creating a New Endpoint

### Step 1: Create Database Migration

Create SQL migration in `supabase/migrations/`:

```sql
-- raw table (stores incoming payloads)
CREATE TABLE raw.your_table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- key identifier fields
    linkedin_url TEXT,
    workflow_slug TEXT,
    -- metadata
    provider TEXT,
    platform TEXT,
    payload_type TEXT,
    -- the actual payload
    raw_payload JSONB,
    -- timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extracted table (flattened/normalized)
CREATE TABLE extracted.your_table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.your_table_name(id),
    -- flattened fields from payload
    field_1 TEXT,
    field_2 TEXT,
    -- timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes as needed
CREATE INDEX idx_your_table_linkedin ON extracted.your_table_name(linkedin_url);
```

Apply via Supabase MCP or dashboard.

### Step 2: Create Extraction Function

Add to `src/extraction/<module>.py`:

```python
from typing import Optional

def extract_your_data(
    supabase,
    raw_payload_id: str,
    identifier: str,  # e.g., linkedin_url
    payload: dict,
) -> Optional[str]:
    """
    Extract data from raw payload to extracted table.
    Returns extracted record ID.
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "field_1": payload.get("field_1"),
        "field_2": payload.get("field_2"),
        # ... more fields
    }

    result = (
        supabase.schema("extracted")
        .from_("your_table_name")
        .insert(extracted_data)
        .execute()
    )

    return result.data[0]["id"] if result.data else None
```

### Step 3: Create Ingest Function

Add to `src/ingest/<module>.py`:

```python
import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.your_module import extract_your_data


class YourRequest(BaseModel):
    identifier: str  # e.g., linkedin_url
    workflow_slug: str
    raw_payload: dict
    optional_field: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_your_endpoint(request: YourRequest) -> dict:
    """
    Ingest your data type.
    Stores raw payload, then extracts to normalized table.
    """
    from supabase import create_client  # Lazy import!

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("your_table_name")
            .insert({
                "identifier": request.identifier,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extracted_id = extract_your_data(
            supabase, raw_id, request.identifier, request.raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Step 4: Update app.py

```python
# Add import
from ingest.your_module import ingest_your_endpoint

# Add to __all__ list
__all__ = [
    # ... existing exports
    "ingest_your_endpoint",
]

# If you created a new extraction module, add explicit import
import extraction.your_module
```

### Step 5: Add Workflow to Registry

```sql
INSERT INTO reference.enrichment_workflow_registry 
(workflow_slug, provider, platform, payload_type, entity_type, description) 
VALUES (
  'your-workflow-slug',
  'clay',           -- or other provider
  'clay',           -- or other platform
  'discovery',      -- or 'enrichment', 'signal', etc.
  'company',        -- or 'person'
  'Description of what this workflow does'
);
```

### Step 6: Deploy

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

---

## Code Patterns

### CORRECT: Function in Separate Module

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
    from supabase import create_client  # Lazy import
    # ... function body
```

**File: `src/app.py`**
```python
from ingest.person import ingest_my_function  # Import only
```

### INCORRECT: Function Inline in app.py

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

**WHY THIS MATTERS:** Modal handles secrets injection differently for imported module functions vs inline definitions. Inline functions fail silently when accessing `os.environ`.

### Lazy Imports

Always import heavy dependencies inside the function body:

```python
@app.function(...)
def my_endpoint(request: MyRequest) -> dict:
    # CORRECT: Import inside function
    from supabase import create_client
    import openai
    
    # ... use them
```

NOT at module level:
```python
# WRONG: Module-level import
from supabase import create_client  # Will fail locally

@app.function(...)
def my_endpoint(request: MyRequest) -> dict:
    # ...
```

### Upsert Pattern

For tables that should have unique records:

```python
result = (
    supabase.schema("extracted")
    .from_("your_table")
    .upsert(extracted_data, on_conflict="linkedin_url")
    .execute()
)
```

---

## Deployment

### Pre-Deployment Checklist

1. **Code committed?**
   ```bash
   git status  # Should show "nothing to commit"
   ```

2. **On main branch?**
   ```bash
   git branch --show-current  # Should show "main"
   ```

3. **Migrations applied?**
   - Check Supabase dashboard or use Supabase MCP

4. **Workflow in registry?**
   ```sql
   SELECT * FROM reference.enrichment_workflow_registry 
   WHERE workflow_slug = 'your-workflow-slug';
   ```

### Deploy Command

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

**NEVER:**
- `modal deploy` (without `uv run`) - dependencies won't be available
- `modal deploy src/ingest/person.py` - individual modules break the app
- Deploy uncommitted code

### Verify Deployment

```bash
# Should return 405 (POST-only endpoints reject GET)
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-your-endpoint.modal.run
```

---

## Naming Conventions

### DNS Label Limit

Function names must result in URLs under 63 characters for the hostname.

Format: `bencrane--hq-master-data-ingest-<function-name>.modal.run`

The prefix `bencrane--hq-master-data-ingest-` is 32 characters, leaving ~30 characters for the function name.

### Abbreviations (when names are too long)

| Full | Abbreviated |
|------|-------------|
| `people` | `ppl` |
| `location` | `lctn` |
| `parsed` | `prsd` |
| `companies` | `co` |
| `company` | `comp` |

Example: `ingest_clay_find_ppl_lctn_prsd`

### Function Naming Patterns

| Pattern | Example | Use For |
|---------|---------|---------|
| `ingest_clay_*` | `ingest_clay_find_people` | Clay data ingestion |
| `ingest_*_signal_*` | `ingest_clay_signal_new_hire` | Signal-type data |
| `lookup_*` | `lookup_job_title` | Reference table queries |
| `backfill_*` | `backfill_person_location` | Batch update operations |

---

## Common Pitfalls

### 1. Secrets Not Available

**Symptom:** `KeyError: 'SUPABASE_URL'`

**Cause:** Function defined inline in `app.py` instead of imported module.

**Fix:** Move function to `ingest/<module>.py` and import it.

### 2. Module Not Found

**Symptom:** `ModuleNotFoundError: No module named 'pydantic'`

**Cause:** Running `modal deploy` without `uv run`.

**Fix:** Always use `uv run modal deploy src/app.py`

### 3. Extraction Not Running

**Symptom:** Raw table has data, extracted table is empty.

**Cause:** Column name mismatch between code and database schema.

**Fix:** Verify column names in extraction function match actual database columns.

### 4. Supabase Returns Max 1000 Rows

**Symptom:** Lookup table only returns 1000 entries.

**Cause:** Supabase default limit.

**Fix:** Paginate with `.range(offset, offset + batch_size - 1)`:

```python
all_data = []
offset = 0
batch_size = 1000
while True:
    result = supabase.schema("reference").from_("table").select("*").range(offset, offset + batch_size - 1).execute()
    if not result.data:
        break
    all_data.extend(result.data)
    if len(result.data) < batch_size:
        break
    offset += batch_size
```

### 5. Endpoint URL Truncated

**Symptom:** Modal shows `(label truncated)` in deploy output.

**Cause:** Function name too long.

**Fix:** Use abbreviations (see Naming Conventions).

---

## Testing

### Dry Run Pattern

For batch operations, always implement dry run:

```python
class BackfillRequest(BaseModel):
    dry_run: bool = True  # Default to safe mode
    limit: Optional[int] = None

@app.function(...)
def backfill_something(request: BackfillRequest) -> dict:
    if request.dry_run:
        # Return preview of what would be updated
        return {"dry_run": True, "would_update": count, "sample": sample_records}
    else:
        # Actually perform updates
        return {"dry_run": False, "updated": updated_count}
```

### Testing Sequence

1. **Dry run** - See what would happen
   ```bash
   curl -X POST <endpoint> -H "Content-Type: application/json" -d '{}'
   ```

2. **Small batch** - Test with limit
   ```bash
   curl -X POST <endpoint> -H "Content-Type: application/json" -d '{"dry_run": false, "limit": 10}'
   ```

3. **Verify** - Check database records

4. **Scale up** - Increase limit gradually

5. **Full run** - Remove limit

### Document Payload Format

When documenting payloads, use empty `{}` for nested objects:

```json
{
  "linkedin_url": "https://www.linkedin.com/in/example/",
  "workflow_slug": "workflow-slug-here",
  "raw_payload": {}
}
```

Do NOT expand full nested payload contents in documentation examples.
