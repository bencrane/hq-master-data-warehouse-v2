# CompanyEnrich Similar Companies: Architecture & Current State

**Last Updated:** 2026-02-17

---

## Overview

CompanyEnrich provides two API endpoints for finding similar companies:

| Endpoint | URL | Payload Type | Fields per Item |
|----------|-----|--------------|-----------------|
| **Preview** | `https://api.companyenrich.com/companies/similar/preview` | Lean | 9 fields |
| **Full** | `https://api.companyenrich.com/companies/similar` | Rich | 24 fields |

Both endpoints return similar companies for a given input domain, but with different levels of firmographic detail.

---

## Payload Comparison

### Preview Payload (Lean)

Each item in the `items` array contains only:

```json
{
  "id": "uuid",
  "name": "Company Name",
  "domain": "example.com",
  "website": "https://example.com",
  "industry": "Software",
  "keywords": ["keyword1", "keyword2"],
  "logo_url": "https://api.companyenrich.com/companies/logo/...",
  "updated_at": "2026-02-14T05:18:31.417283Z",
  "description": "Company description text"
}
```

**9 fields total.**

### Full Payload (Rich)

Each item contains all preview fields PLUS:

```json
{
  // ...preview fields...
  "type": "private",
  "revenue": "1m-10m",
  "employees": "51-200",
  "founded_year": 2015,
  "page_rank": 4.1066356,
  "categories": ["b2b", "saas"],
  "industries": ["Software", "Business Services/Custom Software & IT Services"],
  "naics_codes": ["511210", "518210", "541511"],
  "subsidiaries": null,
  "seo_description": "Extended company description...",
  "socials": {
    "linkedin_url": "https://www.linkedin.com/company/...",
    "linkedin_id": "5213969",
    "twitter_url": "https://twitter.com/...",
    "facebook_url": "https://www.facebook.com/...",
    "instagram_url": "https://www.instagram.com/...",
    "youtube_url": "https://youtube.com/...",
    "github_url": null,
    "g2_url": "https://www.g2.com/products/.../reviews",
    "crunchbase_url": "https://www.crunchbase.com/organization/...",
    "angellist_url": "http://angel.co/..."
  },
  "location": {
    "address": "123 Main St, City, Country",
    "postal_code": "12345",
    "phone": "+1 555-1234",
    "city": {
      "id": 12345,
      "name": "City Name",
      "latitude": 40.12345,
      "longitude": -74.12345
    },
    "state": {
      "id": 123,
      "code": "NY",
      "name": "New York",
      "latitude": 40.0,
      "longitude": -74.0
    },
    "country": {
      "code": "US",
      "name": "United States",
      "latitude": 38.0,
      "longitude": -97.0
    }
  },
  "financial": {
    "funding_stage": "series_a",
    "total_funding": 5000000,
    "funding_date": "2023-01-15T00:00:00",
    "stock_symbol": null,
    "stock_exchange": null,
    "funding": [
      {
        "type": "Series A - Company Name",
        "amount": "5000000 USD",
        "date": "2023-01-15T00:00:00",
        "from": "Investor Name",
        "url": null
      }
    ]
  },
  "technologies": [
    "Amazon AWS",
    "Google Analytics",
    "Salesforce",
    "..."
  ]
}
```

**24 fields total.**

### Response Metadata

Both endpoints return the same top-level structure:

```json
{
  "page": 1,
  "items": [...],
  "metadata": {
    "scores": {
      "company-uuid-1": 0.89,
      "company-uuid-2": 0.87
    }
  },
  "totalItems": 10000,
  "totalPages": 1000
}
```

---

## Current Modal Endpoints

### 1. Direct API Call Endpoint (Preview Only)

**File:** `modal-functions/src/ingest/company_enrich_similar.py`

**Endpoints:**
- `find_similar_companies_single` - Single domain, synchronous
- `find_similar_companies_batch` - Multiple domains, async with background worker
- `get_similar_companies_batch_status` - Check batch progress

**API Called:** `https://api.companyenrich.com/companies/similar/preview`

**Tables Written:**
| Table | Fields Extracted |
|-------|------------------|
| `raw.company_enrich_similar_raw` | Full API response |
| `extracted.company_enrich_similar` | Basic fields only (id, name, domain, industry, description, keywords, logo_url, similarity_score) |

**Does NOT write to:**
- `core.company_similar_companies_preview`
- Any profile/location/socials/financial tables
- Any `core.companies` dimension tables

### 2. Clay Ingest Endpoint (Handles Full Payloads)

**File:** `modal-functions/src/ingest/companyenrich_similar_companies_preview_results.py`

**Endpoint:** `ingest_companyenrich_similar_preview_results`

**Purpose:** Receives CompanyEnrich similar results from Clay webhooks

**Confusing Naming:** Despite being called "preview_results", this endpoint is designed to handle **FULL** payloads and extracts all rich firmographic data.

**Tables Written:**

| Layer | Table | Data Extracted |
|-------|-------|----------------|
| Raw | `raw.company_enrich_similar_raw` | Full payload |
| Extracted | `extracted.company_enrich_similar` | Basic similarity relationship |
| Extracted | `extracted.companyenrich_similar_company_profile` | Full company profile (name, type, employees, revenue, founded_year, etc.) |
| Extracted | `extracted.companyenrich_similar_company_location` | City, state, country, address, lat/long |
| Extracted | `extracted.companyenrich_similar_company_socials` | All social URLs |
| Extracted | `extracted.companyenrich_similar_company_financial` | Funding stage, total funding, stock info |
| Extracted | `extracted.companyenrich_similar_company_funding_rounds` | Each funding round detail |
| Extracted | `extracted.companyenrich_similar_company_technologies` | Each technology (one row per tech) |
| Core | `core.company_similar_companies_preview` | Basic similarity relationship |
| Core | `core.companies` | New company record (if domain doesn't exist) |
| Core | `core.company_descriptions` | Description, tagline |
| Core | `core.company_locations` | City, state, country |
| Core | `core.company_employee_range` | Employee range (via lookup) |
| Core | `core.company_revenue` | Revenue range (via lookup) |
| Core | `core.company_industries` | Industry (via lookup) |
| Core | `core.company_business_model` | B2B/B2C (derived from categories) |
| Core | `core.company_types` | Company type (via lookup) |
| Core | `core.company_social_urls` | All social URLs |
| Core | `core.company_categories` | Each category |
| Core | `core.company_keywords` | Each keyword |
| Core | `core.company_funding` | Total funding |

---

## Database Tables

### Core Tables

| Table | Purpose | Record Count (as of 2026-02-17) |
|-------|---------|--------------------------------|
| `core.company_similar_companies_preview` | Stores similarity relationships (input_domain → similar company) | 137,189 |

**Schema:**
```sql
- id (uuid)
- input_domain (text) -- the domain we searched for
- company_name (text)
- company_domain (text) -- the similar company's domain
- company_industry (text)
- company_description (text)
- similarity_score (numeric)
- source (text, default 'companyenrich')
- created_at, updated_at
```

### Extracted Tables

| Table | Purpose | Record Count |
|-------|---------|--------------|
| `extracted.company_enrich_similar` | Basic similarity relationship | 141,804 |
| `extracted.companyenrich_similar_company_profile` | Full company firmographics | **80** |
| `extracted.companyenrich_similar_company_location` | Company locations | ~80 |
| `extracted.companyenrich_similar_company_socials` | Social media URLs | ~80 |
| `extracted.companyenrich_similar_company_financial` | Funding summary | ~80 |
| `extracted.companyenrich_similar_company_funding_rounds` | Individual funding rounds | varies |
| `extracted.companyenrich_similar_company_technologies` | Technologies used | varies |

### Raw Tables

| Table | Purpose |
|-------|---------|
| `raw.company_enrich_similar_raw` | Full API response storage |
| `raw.company_enrich_similar_batches` | Batch job tracking |
| `raw.company_enrich_similar_queue` | Queue for processing |

---

## Current Data State

### The Problem

| Data Path | Records | Has Full Firmographics? |
|-----------|---------|------------------------|
| Direct API → Preview endpoint | ~141,000 | NO - only basic fields |
| Clay ingest → Full payload | ~80 | YES - all fields |

**98%+ of similar company data lacks rich firmographic information** (employees, revenue, funding, location, socials, technologies).

This happened because:
1. The direct Modal endpoint calls `/similar/preview` (lean API)
2. Only 80 records came through Clay with full payloads
3. The naming was confusing ("preview" used for both lean and full scenarios)

---

## What's Needed

### Option A: New Full Endpoint

Create a new Modal endpoint that:
1. Calls `https://api.companyenrich.com/companies/similar` (full API, not preview)
2. Extracts all 24 fields
3. Writes to all the rich extracted tables (profile, location, socials, financial, technologies)
4. Writes to core dimension tables for new companies

### Option B: Backfill via Clay

Re-run existing similar company domains through Clay with the full CompanyEnrich action, then ingest via the existing Clay endpoint.

### Naming Convention Going Forward

| Endpoint Name | API Called | Data Level |
|---------------|------------|------------|
| `find_similar_companies_preview_*` | `/companies/similar/preview` | Lean (9 fields) |
| `find_similar_companies_full_*` | `/companies/similar` | Rich (24 fields) |

---

## Related Files

| File | Purpose |
|------|---------|
| `modal-functions/src/ingest/company_enrich_similar.py` | Direct API calls to preview endpoint |
| `modal-functions/src/ingest/companyenrich_similar_companies_preview_results.py` | Clay ingest (handles full payloads despite name) |
| `supabase/migrations/` | Table definitions |

---

## API Authentication

CompanyEnrich API requires Bearer token authentication:

```python
headers = {
    "Authorization": f"Bearer {companyenrich_key}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}
```

Modal secret: `companyenrich-api-key` (contains `COMPANYENRICH_API_KEY`)

---

## Questions to Resolve

1. Is there a cost difference between `/similar/preview` and `/similar` endpoints?
2. Should we backfill the ~140k preview records with full data?
3. Do we need both endpoints, or just the full one going forward?
