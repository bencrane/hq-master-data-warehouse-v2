# Data Warehouse Update - February 6, 2026

## Session Summary

This session focused on building **db-direct workflows** - a new pattern where Modal functions call external APIs AND write directly to PostgreSQL via psycopg2 (bypassing Supabase REST client for performance and reduced brittleness).

---

## Architecture Decision: Direct PostgreSQL over Supabase Client

**Decision:** All new db-direct workflows use direct PostgreSQL connections (psycopg2) instead of Supabase Python client.

**Rationale:**
- Less brittle than REST API calls
- Better performance for bulk operations
- More control over transactions
- User explicitly stated: "i 100% do NOT want to be using supabase rest client"

**Pattern:**
```python
import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("INSERT INTO ...")
conn.commit()
```

**Secret:** Modal functions use `modal.Secret.from_name("supabase-db-direct")` with `DATABASE_URL` environment variable.

---

## New DB-Direct Workflows Created

### 1. B2B/B2C Classification (OpenAI)

**Endpoint:** `POST /run/companies/openai-native/b2b-b2c/classify/db-direct`

**Modal Function:** `classify_b2b_b2c_openai_db_direct.py`

**Modal URL:** `https://bencrane--hq-master-data-ingest-classify-b2b-b2c-openai-db-direct.modal.run`

**Flow:**
1. Receive domain, company_name, description
2. Call OpenAI to classify B2B/B2C
3. Write to `raw.company_classification_db_direct`
4. Write to `extracted.company_classification_db_direct`
5. Write to `core.company_business_model`

**Tables Required:**
```sql
-- raw.company_classification_db_direct
CREATE TABLE raw.company_classification_db_direct (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT NOT NULL,
    company_name TEXT,
    description TEXT,
    model TEXT,
    prompt TEXT,
    response JSONB,
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extracted.company_classification_db_direct
CREATE TABLE extracted.company_classification_db_direct (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_id TEXT,
    domain TEXT UNIQUE NOT NULL,
    is_b2b BOOLEAN,
    b2b_reason TEXT,
    is_b2c BOOLEAN,
    b2c_reason TEXT,
    model TEXT,
    workflow_source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- core.company_business_model
CREATE TABLE core.company_business_model (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    is_b2b BOOLEAN,
    is_b2c BOOLEAN,
    workflow_source TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 2. LinkedIn Ads Ingestion (Adyntel)

**Endpoint:** `POST /run/companies/adyntel-native/linkedin-ads/ingest/db-direct`

**Modal Function:** `ingest_linkedin_ads_db_direct.py`

**Modal URL:** `https://bencrane--hq-master-data-ingest-ingest-linkedin-ads-db-direct.modal.run`

**Flow:**
1. Receive domain, linkedin_ads_payload
2. Write raw payload to `raw.linkedin_ads_payloads`
3. Extract individual ads to `extracted.company_linkedin_ads`
4. Update summary in `core.company_linkedin_ads`

**Tables Required:**
```sql
-- raw.linkedin_ads_payloads
CREATE TABLE raw.linkedin_ads_payloads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extracted.company_linkedin_ads
CREATE TABLE extracted.company_linkedin_ads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_payload_id TEXT,
    domain TEXT NOT NULL,
    ad_id TEXT UNIQUE,
    ad_type TEXT,
    creative_type TEXT,
    headline_title TEXT,
    headline_description TEXT,
    commentary_text TEXT,
    image_url TEXT,
    image_alt_text TEXT,
    advertiser_name TEXT,
    view_details_link TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- core.company_linkedin_ads (add workflow_source)
ALTER TABLE core.company_linkedin_ads ADD COLUMN IF NOT EXISTS workflow_source TEXT;
```

---

### 3. Meta Ads Ingestion (Adyntel)

**Endpoint:** `POST /run/companies/adyntel-native/meta-ads/ingest/db-direct`

**Modal Function:** `ingest_meta_ads_db_direct.py`

**Modal URL:** `https://bencrane--hq-master-data-ingest-ingest-meta-ads-db-direct.modal.run`

**Flow:**
1. Receive domain, meta_ads_payload
2. Write raw payload to `raw.meta_ads_payloads`
3. Extract individual ads to `extracted.company_meta_ads`
4. Update summary in `core.company_meta_ads`

**Tables Required:**
```sql
-- raw.meta_ads_payloads
CREATE TABLE raw.meta_ads_payloads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extracted.company_meta_ads
CREATE TABLE extracted.company_meta_ads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_payload_id TEXT,
    domain TEXT NOT NULL,
    ad_id TEXT UNIQUE,
    platform TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    page_name TEXT,
    ad_creative_body TEXT,
    ad_creative_link_title TEXT,
    ad_creative_link_description TEXT,
    landing_page_url TEXT,
    image_url TEXT,
    video_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- core.company_meta_ads (add workflow_source)
ALTER TABLE core.company_meta_ads ADD COLUMN IF NOT EXISTS workflow_source TEXT;
```

---

### 4. Google Ads Ingestion (Adyntel)

**Endpoint:** `POST /run/companies/adyntel-native/google-ads/ingest/db-direct`

**Modal Function:** `ingest_google_ads_db_direct.py`

**Modal URL:** `https://bencrane--hq-master-data-ingest-ingest-google-ads-db-direct.modal.run`

**Flow:**
1. Receive domain, google_ads_payload
2. Write raw payload to `raw.google_ads_payloads`
3. Extract individual creatives to `extracted.company_google_ads`
4. Update summary in `core.company_google_ads`

**Tables Required:**
```sql
-- raw.google_ads_payloads
CREATE TABLE raw.google_ads_payloads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    domain TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- extracted.company_google_ads
CREATE TABLE extracted.company_google_ads (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    raw_payload_id TEXT,
    domain TEXT NOT NULL,
    creative_id TEXT UNIQUE,
    advertiser_id TEXT,
    ad_type TEXT,
    first_shown TEXT,
    last_shown TEXT,
    text_content TEXT,
    image_url TEXT,
    video_url TEXT,
    landing_page_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- core.company_google_ads (add workflow_source)
ALTER TABLE core.company_google_ads ADD COLUMN IF NOT EXISTS workflow_source TEXT;
```

---

### 5. Company Description Inference (Parallel AI)

**Endpoints:**
- `POST /run/companies/parallel-native/description/infer/db-direct` (single)
- `POST /run/companies/parallel-native/description/infer/db-direct/batch` (batch)

**Modal Function:** `infer_description_db_direct.py`

**Modal URL:** `https://bencrane--hq-master-data-ingest-infer-description-db-direct.modal.run`

**Flow:**
1. Receive domain, company_name, company_linkedin_url
2. Submit task to Parallel AI Task Enrichment API
3. Poll for completion (30 attempts, 2-second intervals)
4. Write to `core.company_descriptions`

**API Used:** Parallel AI Task Enrichment API
- URL: `https://api.parallel.ai/v1/tasks/runs`
- Pattern: Async (submit → poll for completion)

**Table:** `core.company_descriptions` (add workflow_source column)
```sql
ALTER TABLE core.company_descriptions ADD COLUMN IF NOT EXISTS workflow_source TEXT;
```

---

## Parallel AI API Reference

### Processor Options

| Processor | Speed | Use Case |
|-----------|-------|----------|
| `lite` | 10-60s | Basic tasks, lightweight |
| `lite-fast` | 3-5x faster | Quick subagent calls |
| `base` | 15-100s | Standard complexity |
| `core` | 1-5min | Balanced, strong at many tasks |
| `core2x` | 2-10min | High complexity, cross-referenced |
| `pro` | 2-10min | Exploratory web research |
| `ultra` | Longest | Most demanding operations |

### API Request Structure

```python
{
    "input": { ... },           # Your input data
    "processor": "core",        # or "lite", "lite-fast", "base", "pro", "ultra"
    "task_spec": {
        "input_schema": { ... },   # JSON Schema for inputs
        "output_schema": { ... }   # JSON Schema for desired outputs
    }
}
```

---

## Modal Secrets Required

| Secret Name | Environment Variable | Purpose |
|-------------|---------------------|---------|
| `supabase-db-direct` | `DATABASE_URL` | Direct PostgreSQL connection string |
| `openai-secret` | `OPENAI_API_KEY` | OpenAI API access |
| `parallel-secret` | `PARALLEL_API_KEY` | Parallel AI API access |

**DATABASE_URL format:**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

---

## MCP Configuration (Cursor)

Added three Parallel AI MCPs to `~/.cursor/mcp.json`:

```json
{
  "parallel-search": {
    "url": "https://search-mcp.parallel.ai/mcp",
    "headers": {
      "Authorization": "Bearer [PARALLEL_API_KEY]"
    }
  },
  "parallel-task": {
    "url": "https://task-mcp.parallel.ai/mcp",
    "headers": {
      "Authorization": "Bearer [PARALLEL_API_KEY]"
    }
  },
  "parallel-docs": {
    "url": "https://docs-mcp.parallel.ai/mcp",
    "headers": {
      "Authorization": "Bearer [PARALLEL_API_KEY]"
    }
  }
}
```

**MCP Tools:**
- `parallel-search` - Web search
- `parallel-task` - Deep research + enrichment task groups
- `parallel-docs` - Search Parallel's knowledge base/API docs (meta MCP)

---

## Naming Convention

**API Endpoints:** `/run/{entity}/{platform}/{workflow}/{action}/db-direct`

**Examples:**
- `/run/companies/openai-native/b2b-b2c/classify/db-direct`
- `/run/companies/adyntel-native/linkedin-ads/ingest/db-direct`
- `/run/companies/parallel-native/description/infer/db-direct`

**Workflow Source:** `{platform}/{workflow}/{action}/db-direct`

**Examples:**
- `openai-native/b2b-b2c/classify/db-direct`
- `adyntel-native/linkedin-ads/ingest/db-direct`
- `parallel-native/description/infer/db-direct`

---

## TTL-Based Refresh Logic

All db-direct endpoints support `ttl_days` parameter:
- `None` (default) = Skip if exists
- `0` = Always refresh
- `N` = Refresh if older than N days

---

## Files Created/Modified

### New Modal Functions (`/modal/`)
- `classify_b2b_b2c_openai_db_direct.py`
- `ingest_linkedin_ads_db_direct.py`
- `ingest_meta_ads_db_direct.py`
- `ingest_google_ads_db_direct.py`
- `infer_description_db_direct.py`

### Modified API (`/hq-api/routers/run.py`)
- Added 6 new db-direct endpoints (5 single + 1 batch)
- Lines ~6230-6950

### MCP Config
- `~/.cursor/mcp.json` - Added 3 Parallel AI MCPs

---

## Deployment Checklist

### 1. Create Modal Secret
```bash
modal secret create supabase-db-direct DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
```

### 2. Create Database Tables
Run SQL migrations for each new workflow (see table definitions above).

### 3. Deploy Modal Functions
```bash
cd modal
modal deploy classify_b2b_b2c_openai_db_direct.py
modal deploy ingest_linkedin_ads_db_direct.py
modal deploy ingest_meta_ads_db_direct.py
modal deploy ingest_google_ads_db_direct.py
modal deploy infer_description_db_direct.py
```

### 4. Deploy HQ API
Push to GitHub → Railway auto-deploys.

---

## Next Steps / Pending Work

1. **Create `supabase-db-direct` Modal secret** with DATABASE_URL
2. **Run SQL migrations** to create tables
3. **Deploy Modal functions**
4. **Test each endpoint** end-to-end
5. **Build discrete enrichment workflows** for Parallel AI:
   - Revenue
   - Employee count
   - Funding raised
   - Last funding date
   - (Each as separate endpoint following same pattern)

---

## Key Understanding for Future AI

1. **db-direct = Direct PostgreSQL** - No Supabase REST client
2. **Modal handles external API calls** - API → Modal → External API → DB
3. **raw/extracted/core pattern** - Data flows through all three schemas
4. **workflow_source for provenance** - Track where data came from
5. **TTL-based refresh** - Control when to re-enrich
6. **Parallel AI is async** - Submit task, poll for results
7. **User prefers discrete enrichments** - One data point per endpoint, then combine
