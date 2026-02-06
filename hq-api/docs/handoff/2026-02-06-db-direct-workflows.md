# Handoff: DB-Direct Workflows

**Date:** 2026-02-06
**Status:** In Progress - Deployment Phase

---

## Context

Building a new pattern of "db-direct" workflows where Modal functions:
1. Receive requests from HQ API
2. Call external APIs (OpenAI, Parallel AI, Adyntel)
3. Write directly to PostgreSQL using psycopg2 (NOT Supabase REST client)

This is the preferred pattern going forward.

---

## What Was Completed

### Code Written

1. **5 Modal Functions** in `/modal/`:
   - `classify_b2b_b2c_openai_db_direct.py` - B2B/B2C classification via OpenAI
   - `ingest_linkedin_ads_db_direct.py` - LinkedIn ads from Adyntel
   - `ingest_meta_ads_db_direct.py` - Meta ads from Adyntel
   - `ingest_google_ads_db_direct.py` - Google ads from Adyntel
   - `infer_description_db_direct.py` - Company descriptions via Parallel AI

2. **6 API Endpoints** in `/hq-api/routers/run.py` (lines ~6230-6950):
   - `POST /run/companies/openai-native/b2b-b2c/classify/db-direct`
   - `POST /run/companies/adyntel-native/linkedin-ads/ingest/db-direct`
   - `POST /run/companies/adyntel-native/meta-ads/ingest/db-direct`
   - `POST /run/companies/adyntel-native/google-ads/ingest/db-direct`
   - `POST /run/companies/parallel-native/description/infer/db-direct`
   - `POST /run/companies/parallel-native/description/infer/db-direct/batch`

3. **MCP Configuration** - Added 3 Parallel AI MCPs to `~/.cursor/mcp.json`:
   - `parallel-search`
   - `parallel-task`
   - `parallel-docs`

### Secrets Already Created (by user)
- `openai-secret` - OpenAI API key
- `parallel-secret` - Parallel AI API key

---

## What's Blocking Deployment

### 1. Missing Modal Secret: `supabase-db-direct`

All new Modal functions use:
```python
db_secret = modal.Secret.from_name("supabase-db-direct")
```

And expect:
```python
conn = psycopg2.connect(os.environ["DATABASE_URL"])
```

**User needs to create:**
```bash
modal secret create supabase-db-direct DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"
```

The DATABASE_URL is the direct PostgreSQL connection string from Supabase:
- Dashboard → Settings → Database → Connection string → URI format

---

### 2. Database Tables Not Created

The following tables need to be created:

**B2B/B2C Classification:**
- `raw.company_classification_db_direct`
- `extracted.company_classification_db_direct`
- `core.company_business_model`

**LinkedIn Ads:**
- `raw.linkedin_ads_payloads`
- `extracted.company_linkedin_ads`
- (core table exists, needs `workflow_source` column)

**Meta Ads:**
- `raw.meta_ads_payloads`
- `extracted.company_meta_ads`
- (core table exists, needs `workflow_source` column)

**Google Ads:**
- `raw.google_ads_payloads`
- `extracted.company_google_ads`
- (core table exists, needs `workflow_source` column)

**Company Descriptions:**
- (core table exists, needs `workflow_source` column)

See `/docs/data-mapping/data_warehouse_update_2026_02_06.md` for full SQL.

---

## Deployment Steps (In Order)

```bash
# 1. Create Modal secret (user must do this)
modal secret create supabase-db-direct DATABASE_URL="postgresql://..."

# 2. Run SQL migrations in Supabase
# (Copy from data_warehouse_update_2026_02_06.md)

# 3. Deploy Modal functions
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal
modal deploy classify_b2b_b2c_openai_db_direct.py
modal deploy ingest_linkedin_ads_db_direct.py
modal deploy ingest_meta_ads_db_direct.py
modal deploy ingest_google_ads_db_direct.py
modal deploy infer_description_db_direct.py

# 4. HQ API auto-deploys on git push
```

---

## Testing After Deployment

### Test B2B/B2C Classification
```bash
curl -X POST "https://hq-master-data-api-production.up.railway.app/run/companies/openai-native/b2b-b2c/classify/db-direct" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "stripe.com",
    "company_name": "Stripe",
    "description": "Financial infrastructure for the internet"
  }'
```

### Test Description Inference
```bash
curl -X POST "https://hq-master-data-api-production.up.railway.app/run/companies/parallel-native/description/infer/db-direct" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "stripe.com",
    "company_name": "Stripe"
  }'
```

---

## Future Work (User's Intent)

User wants to build **discrete enrichment endpoints** for each data point:
- Revenue
- Employee count
- Funding raised
- Last funding date
- etc.

Each as a separate `/run/companies/parallel-native/{datapoint}/infer/db-direct` endpoint.

User explicitly stated: "I prefer building discretely first" - meaning one data point per endpoint, not batching multiple enrichments together.

---

## Key Files

| File | Purpose |
|------|---------|
| `/modal/infer_description_db_direct.py` | Parallel AI description inference |
| `/modal/classify_b2b_b2c_openai_db_direct.py` | OpenAI B2B/B2C classification |
| `/modal/ingest_*_ads_db_direct.py` | Adyntel ads ingestion (3 files) |
| `/hq-api/routers/run.py` | All API endpoints (lines 6230-6950) |
| `/docs/data-mapping/data_warehouse_update_2026_02_06.md` | Full documentation |
| `~/.cursor/mcp.json` | Parallel AI MCP configuration |

---

## Important Notes

1. **DO NOT use Supabase REST client** - User explicitly wants direct PostgreSQL only
2. **Existing Modal functions use different secret** - `supabase-credentials` with `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` for REST API. New db-direct functions need different secret.
3. **Parallel AI is async** - Submit task, poll for results (not instant)
4. **User has Parallel AI API key** - `LBGQ8CjfxZfPqqA7g1BDQS-_ci0BWtzeznqyDR6m`
