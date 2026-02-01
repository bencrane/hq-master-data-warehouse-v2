# Data Ingestion Protocol

Standard protocol for building Clay → Database ingestion flows with auto-populated reference tables.

## Overview

This pattern ingests enrichment data from Clay webhooks into a 4-layer schema, enabling UI search/filter without manual mapping.

## Schema Layers

| Layer | Schema | Purpose | Example Table |
|-------|--------|---------|---------------|
| 1. Raw | `raw` | Store full JSON payload unchanged | `raw.builtwith_payloads` |
| 2. Extracted | `extracted` | Flatten arrays, one row per entity | `extracted.company_builtwith` |
| 3. Reference | `reference` | Auto-populated lookup catalog | `reference.technologies` |
| 4. Core | `core` | Normalized mapping for queries | `core.company_technologies` |

## Step-by-Step Protocol

### Step 1: Design Tables

**Raw Table** - Store the full payload for debugging/reprocessing:
```sql
CREATE TABLE raw.<source>_payloads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,                    -- Primary key from source
    payload JSONB NOT NULL,                  -- Full JSON unchanged
    clay_table_url TEXT,                     -- Source tracking
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON raw.<source>_payloads(domain);
```

**Extracted Table** - Flatten nested arrays, one row per item:
```sql
CREATE TABLE extracted.company_<entity> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload_id UUID REFERENCES raw.<source>_payloads(id),
    domain TEXT NOT NULL,
    <entity>_name TEXT NOT NULL,             -- The key field to extract
    <additional_fields>,                     -- Other useful fields
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON extracted.company_<entity>(domain);
CREATE INDEX ON extracted.company_<entity>(<entity>_name);
```

**Reference Table** - Auto-populated catalog with UNIQUE constraint:
```sql
CREATE TABLE reference.<entities> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,               -- UNIQUE enables ON CONFLICT
    <metadata_fields>,                       -- url, description, categories, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ON reference.<entities>(name);
```

**Core Table** - Domain ↔ entity_id mapping for queries:
```sql
CREATE TABLE core.company_<entities> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    <entity>_id UUID NOT NULL REFERENCES reference.<entities>(id),
    <tracking_fields>,                       -- first_detected, last_detected, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(domain, <entity>_id)              -- Prevent duplicates
);
CREATE INDEX ON core.company_<entities>(domain);
CREATE INDEX ON core.company_<entities>(<entity>_id);
```

### Step 2: Create Modal Endpoint

Location: `/modal-functions/src/ingest/<source>.py`

```python
"""
<Source> Ingest Endpoint

Expects:
{
  "domain": "example.com",
  "<source>_payload": { ... },
  "clay_table_url": "optional"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_<source>(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("<source>_payload", {})
        clay_table_url = request.get("clay_table_url")

        # Extract the array from payload (handle wrapper objects)
        if isinstance(payload, dict) and "<items_key>" in payload:
            items = payload.get("<items_key>", [])
        elif isinstance(payload, list):
            items = payload
        else:
            return {"success": False, "error": "Invalid payload structure"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("<source>_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Process each item
        count = 0
        for item in items:
            if not isinstance(item, dict):
                continue

            name = item.get("Name") or item.get("name")
            if not name:
                continue

            # Extract additional fields
            field1 = item.get("Field1")
            field2 = item.get("Field2")

            # Insert into extracted
            supabase.schema("extracted").from_("company_<entity>").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "<entity>_name": name,
                "field1": field1,
                "field2": field2,
            }).execute()

            # Upsert into reference (ON CONFLICT DO NOTHING equivalent)
            supabase.schema("reference").from_("<entities>").upsert({
                "name": name,
                "field1": field1,
                "field2": field2,
            }, on_conflict="name").execute()

            # Get reference ID and map to core
            ref = (
                supabase.schema("reference")
                .from_("<entities>")
                .select("id")
                .eq("name", name)
                .limit(1)
                .execute()
            )

            if ref.data:
                entity_id = ref.data[0]["id"]
                supabase.schema("core").from_("company_<entities>").upsert({
                    "domain": domain,
                    "<entity>_id": entity_id,
                }, on_conflict="domain,<entity>_id").execute()

            count += 1

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "<entity>_count": count,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
```

### Step 3: Deploy Modal Endpoint

```bash
cd /modal-functions/src
modal deploy ingest/<source>.py
```

Output will show endpoint URL:
```
https://bencrane--hq-master-data-ingest-ingest-<source>.modal.run
```

### Step 4: Configure Clay Webhook

In Clay:
1. Add HTTP POST action
2. Set URL to Modal endpoint
3. Map fields:
```json
{
  "domain": "/domain",
  "<source>_payload": "/<enrichment_column>",
  "clay_table_url": "https://app.clay.com/..."
}
```

### Step 5: Build Query Endpoints (Optional)

Add to `/hq-api/routers/` for UI consumption:

```python
@router.get("/companies/by-<entity>")
async def get_companies_by_entity(name: str):
    # Join core.company_<entities> with reference.<entities>
    pass

@router.get("/filters/<entities>")
async def get_entity_options():
    # Return distinct names from reference.<entities> for autocomplete
    pass
```

## Key Principles

1. **Raw is sacred** - Never modify raw payloads; store exactly what was received
2. **Reference auto-populates** - Use UNIQUE + ON CONFLICT to build catalog automatically
3. **Core enables queries** - Normalized IDs allow efficient joins and filters
4. **Extracted preserves lineage** - Links back to raw_payload_id for debugging

## Example: BuiltWith Implementation

**Tables Created:**
- `raw.builtwith_payloads`
- `extracted.company_builtwith`
- `reference.technologies`
- `core.company_technologies`

**Modal Endpoint:**
- `ingest/builtwith.py`
- URL: `https://bencrane--hq-master-data-ingest-ingest-builtwith.modal.run`

**Payload Structure:**
```json
{
  "domain": "example.com",
  "builtwith_payload": {
    "matchesFound": [
      {"Name": "jQuery", "Link": "...", "Categories": "JavaScript Library"},
      {"Name": "React", "Link": "...", "Categories": "JavaScript Library"}
    ],
    "technologiesFound": "jQuery, React",
    "numberOfTotalTechnologies": 2
  }
}
```

**Result:** User can search "React" in UI and see all companies using React.
