# Modal Infrastructure Onboarding

**Last Updated:** 2026-01-24  
**App Name:** `hq-master-data-ingest`  
**Dashboard:** https://modal.com/apps/bencrane/main/deployed/hq-master-data-ingest

---

## Purpose

This Modal application is the data ingestion layer for the HQ Master Data Warehouse. It receives data from external sources (primarily Clay), processes it, and stores it in Supabase with a raw → extracted pattern.

---

## Quick Start

### Deploy Command
```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

**CRITICAL:** Always use `uv run` - never bare `modal deploy`.

### Test Deployment
```bash
curl -X POST https://bencrane--hq-master-data-ingest-test-endpoint.modal.run \
  -H "Content-Type: application/json" \
  -d '{"test": "hello"}'
```

---

## Architecture Overview

### Data Flow
```
External Source (Clay, etc.)
        ↓
   Modal Endpoint (ingest function)
        ↓
   raw.* table (JSONB payload)
        ↓
   Extraction function
        ↓
   extracted.* table (flattened fields)
```

### File Structure
```
modal-mcp-server/src/
├── app.py              # ENTRY POINT - imports all modules, deploy this only
├── config.py           # Shared app and image definition
├── ingest/             # Endpoint functions (receive data, store to raw, call extraction)
│   ├── company.py
│   ├── person.py
│   ├── lookup.py       # Reference table queries
│   ├── backfill.py     # Batch update operations
│   ├── signal_*.py     # Signal-type ingestion
│   └── ...
├── extraction/         # Extraction functions (flatten raw payload to extracted tables)
│   ├── company.py
│   ├── person.py
│   └── ...
└── icp/                # ICP generation (uses OpenAI)
    └── generation.py
```

### Key Concepts

1. **Single Entry Point:** All deployments use `app.py`. Individual modules are never deployed separately.

2. **Lazy Imports:** Heavy dependencies (supabase, openai) are imported inside function bodies, not at module level. This is required for Modal compatibility.

3. **Secrets:** Configured in Modal dashboard under `supabase-credentials` and `openai-secret`.

4. **Raw → Extracted Pattern:** Every data type has a `raw.*` table (stores original JSONB) and `extracted.*` table (flattened/normalized fields).

---

## Endpoint Categories

### Ingest Endpoints
Receive data from external sources, store raw, and extract.

| Category | Count | Examples |
|----------|-------|----------|
| Company | 6 | `ingest_clay_company_firmo`, `ingest_clay_find_companies` |
| Person | 4 | `ingest_clay_person_profile`, `ingest_clay_find_people` |
| Signals | 5 | `ingest_clay_signal_new_hire`, `ingest_clay_signal_promotion` |
| Other | 5 | `ingest_vc_portfolio`, `ingest_case_study_extraction` |

### Lookup Endpoints
Query reference tables without storing data.

| Endpoint | Table |
|----------|-------|
| `lookup_person_location` | `reference.location_lookup` |
| `lookup_salesnav_location` | `reference.salesnav_location_lookup` |
| `lookup_salesnav_company_location` | `reference.salesnav_company_location_lookup` |
| `lookup_job_title` | `reference.job_title_lookup` |
| `ingest_clay_company_location_lookup` | `reference.clay_find_companies_location_lookup` |
| `ingest_clay_person_location_lookup` | `reference.clay_find_people_location_lookup` |

### Backfill Endpoints
Batch update extracted tables from reference data.

| Endpoint | Purpose |
|----------|---------|
| `backfill_person_location` | Populate city/state/country in person_discovery from lookup |

### Utility Endpoints
| Endpoint | Purpose |
|----------|---------|
| `test_endpoint` | Echo test for verifying deployment |
| `generate_target_client_icp` | Generate ICP criteria via OpenAI |

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [Modal Development Guide](./modal-development-guide.md) | How to create new endpoints |
| [Modal Endpoints Reference](./MODAL_ENDPOINTS.md) | Full API reference with payloads |
| [Modal Changelog](./MODAL_CHANGELOG.md) | History of changes |

### Historical / Archive
| Document | Purpose |
|----------|---------|
| [MODAL_INFRASTRUCTURE_WORK.md](./MODAL_INFRASTRUCTURE_WORK.md) | (Archive) January 2026 infrastructure rebuild |
| [MODAL_CODE_VERIFICATION.md](./MODAL_CODE_VERIFICATION.md) | (Archive) One-time verification from Jan 6, 2026 |
| [modal-fixes/FIX-001-*.md](./modal-fixes/) | Post-mortem fix documents |

---

## Database Schemas

### Raw Tables (store original payloads)
- `raw.company_payloads`
- `raw.company_discovery`
- `raw.person_payloads`
- `raw.person_discovery`
- `raw.vc_portfolio_payloads`
- `raw.signal_*` (multiple signal tables)

### Extracted Tables (flattened/normalized)
- `extracted.company_firmographics`
- `extracted.company_discovery`
- `extracted.person_profile`
- `extracted.person_discovery`
- `extracted.vc_portfolio`
- `extracted.signal_*` (multiple signal tables)

### Reference Tables (lookups)
- `reference.enrichment_workflow_registry`
- `reference.location_lookup`
- `reference.job_title_lookup`
- `reference.clay_find_people_location_lookup`
- `reference.clay_find_companies_location_lookup`
- `reference.salesnav_location_lookup`
- `reference.salesnav_company_location_lookup`

---

## Common Tasks

### Adding a New Endpoint
See [Modal Development Guide](./modal-development-guide.md)

### Checking Deployment Status
```bash
# All endpoints should return 405 for GET (they're POST-only)
curl -s -o /dev/null -w "%{http_code}" https://bencrane--hq-master-data-ingest-<endpoint-name>.modal.run
```

### Viewing Logs
Go to Modal dashboard → Apps → hq-master-data-ingest → Logs

---

## Rules (Non-Negotiable)

1. **Always commit before deploy** - No exceptions
2. **Always deploy from `app.py`** - Never individual modules
3. **Always use `uv run modal deploy`** - Not bare `modal deploy`
4. **Never delete code** - Mark as disabled/archived instead
5. **Test with small batches first** - Use `dry_run` and `limit` parameters

---

## Disabled/Inactive Code

The following are currently disabled but preserved:

| Item | Location | Reason |
|------|----------|--------|
| `ingest_salesnav_scrapes_person` | `ingest/salesnav_person.py` | Temporarily disabled |
| `extraction.salesnav_person` | `extraction/salesnav_person.py` | Temporarily disabled |
