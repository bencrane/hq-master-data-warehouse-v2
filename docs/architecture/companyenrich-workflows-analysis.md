# CompanyEnrich Workflows Analysis

Two distinct ingest endpoints consume data from the CompanyEnrich API. Both receive data via Clay webhooks and follow the raw -> extracted -> core pipeline pattern, but they serve different purposes, handle different payload structures, and are at different stages of maturity.

---

## Workflow 1: CompanyEnrich Firmo (`companyenrich.py`)

### Purpose

Full firmographic enrichment for a single company. Clay calls this endpoint when it enriches a specific domain through the CompanyEnrich company lookup API. This is a **1 domain in, 1 profile out** workflow.

### Trigger

Clay webhook POSTs `{ domain, raw_payload }` where `raw_payload` is the full CompanyEnrich response for that one domain.

### Data Flow

```
Clay webhook
  -> raw.companyenrich_payloads (INSERT — full payload)
  -> extracted.companyenrich_company (UPSERT on domain — flattened main record)
  -> extracted.companyenrich_keywords (UPSERT on domain,keyword)
  -> extracted.companyenrich_technologies (UPSERT on domain,technology)
  -> extracted.companyenrich_industries (UPSERT on domain,industry)
  -> extracted.companyenrich_categories (UPSERT on domain,category)
  -> extracted.companyenrich_naics_codes (UPSERT on domain,naics_code)
  -> extracted.companyenrich_funding_rounds (UPSERT on domain,funding_date,funding_type)
  -> extracted.companyenrich_investors (UPSERT on domain,investor_name)
  -> extracted.companyenrich_vc_investments (UPSERT on domain,investor_name,funding_date,funding_type)
  -> extracted.companyenrich_socials (UPSERT on domain)
  -> extracted.companyenrich_location (UPSERT on domain)
  -> extracted.companyenrich_subsidiaries (UPSERT on domain,subsidiary_name)
```

### Core Writes

This endpoint writes to core **aggressively and unconditionally** (upserts). It treats CompanyEnrich as a first-class enrichment source and writes/overwrites core dimension tables directly.

| Core Table | Conflict Strategy | Notes |
|---|---|---|
| `core.companies` | Check-then-insert (skip if exists) | domain, name, linkedin_url |
| `core.company_names` | Check-then-insert per source | raw_name, linkedin_url |
| `core.company_employee_range` | UPSERT on domain | Uses `reference.employee_range_lookup` to normalize |
| `core.company_revenue` | UPSERT on domain,source | Uses `reference.revenue_range_lookup` to normalize |
| `core.company_types` | UPSERT on domain,source | Maps via COMPANY_TYPE_MAP (private/public/self-owned) |
| `core.company_descriptions` | UPSERT on domain | description + seo_description as tagline |
| `core.company_locations` | UPSERT on domain | Only writes if incoming has >= fields as existing |
| `core.company_industries` | Check-then-insert (skip if domain has any) | Uses `reference.industry_lookup` to normalize |
| `core.company_keywords` | UPSERT on domain,keyword | One row per keyword |
| `core.company_categories` | UPSERT on domain,category | One row per category |
| `core.company_naics_codes` | UPSERT on domain,naics_code | One row per code |
| `core.company_tech_on_site` | UPSERT on domain,technology_id | Looks up/creates `reference.technologies` first |
| `core.company_social_urls` | UPSERT on domain | All social URLs in one row |
| `core.company_funding_rounds` | UPSERT on domain,source,funding_date,funding_type | Individual rounds |
| `core.company_vc_investors` | UPSERT on company_domain,vc_name | Parsed from funding round `from` field |
| `core.company_vc_backed` | UPSERT on domain | vc_count derived from unique investors |

### Core Tables NOT Written To

- `core.company_funding` (summary table — populated by `company_discovery` pipeline)
- `core.company_business_model` (is_b2b/is_b2c booleans — populated by other pipeline)

### Source Tag

`"companyenrich"` on all core writes.

### Maturity

Stable and battle-tested. 12 extracted breakout tables, 16 core table writes, reference table lookups for normalization. This is the most comprehensive single-endpoint ingest in the codebase.

---

## Workflow 2: Similar Companies Preview (`companyenrich_similar_companies_preview_results.py`)

### Purpose

When we call CompanyEnrich's `similar/preview` endpoint for a given domain, it returns **10 similar companies with full profiles** — essentially 10 free firmographic enrichments. The original version of this endpoint only extracted the similarity relationship (which company is similar to which, with a score). The updated version now also extracts the full company profile from each item.

This is a **1 domain in, 10 profiles out** workflow.

### Trigger

Clay webhook POSTs `{ input_domain, payload }` where `payload.items` is an array of 10 company objects, each with a full CompanyEnrich profile.

### Data Flow

```
Clay webhook
  -> raw.company_enrich_similar_raw (INSERT — full payload with all 10 items)

  For each of 10 items:
    -> extracted.company_enrich_similar (INSERT — similarity relationship: input_domain <-> company_domain + score)
    -> core.company_similar_companies_preview (UPSERT on input_domain,company_domain — similarity record)

    -> extracted.companyenrich_similar_company_profile (UPSERT on domain)
    -> extracted.companyenrich_similar_company_location (UPSERT on domain)
    -> extracted.companyenrich_similar_company_socials (UPSERT on domain)
    -> extracted.companyenrich_similar_company_technologies (UPSERT on domain,technology)
    -> extracted.companyenrich_similar_company_financial (UPSERT on domain)
    -> extracted.companyenrich_similar_company_funding_rounds (UPSERT on domain,funding_type,funding_date)

    -> [CORE WRITES — only if domain not already in core.companies]
```

### Extracted Tables

**Pre-existing (similarity relationship):**
- `extracted.company_enrich_similar` — one row per similar company per input domain, stores the relationship + score
- `core.company_similar_companies_preview` — deduplicated version of above

**New (full profile extraction):**
- `extracted.companyenrich_similar_company_profile` — main firmographic record, keyed on domain
- `extracted.companyenrich_similar_company_location` — location breakout, keyed on domain
- `extracted.companyenrich_similar_company_socials` — social URLs, keyed on domain
- `extracted.companyenrich_similar_company_technologies` — one row per (domain, technology)
- `extracted.companyenrich_similar_company_financial` — funding summary, keyed on domain
- `extracted.companyenrich_similar_company_funding_rounds` — one row per (domain, funding_type, funding_date)

### Core Writes

The endpoint currently attempts to write to core dimension tables, but **only for domains that don't already exist in `core.companies`**. This is the check-then-insert pattern: if the domain is already known (from firmo or another source), all core writes are skipped.

| Core Table | Status | Issue |
|---|---|---|
| `core.companies` | Working | Check-then-insert |
| `core.company_descriptions` | Working | UPSERT on domain |
| `core.company_locations` | Working | UPSERT on domain |
| `core.company_employee_range` | Working | Uses reference lookup |
| `core.company_revenue` | Working | Uses reference lookup |
| `core.company_industries` | Working | Uses reference lookup |
| `core.company_types` | Working | Uses COMPANY_TYPE_MAP |
| `core.company_social_urls` | Working | UPSERT on domain |
| `core.company_categories` | Working | UPSERT on domain,category |
| `core.company_keywords` | Working | UPSERT on domain,keyword |
| `core.company_business_model` | **BROKEN** | Writes `business_model` (text) + `source` but table has `is_b2b`/`is_b2c` (bool) columns, no `source` column. Fails silently. |
| `core.company_funding` | **BROKEN** | Writes `total_funding` but table has `raw_funding_range`/`raw_funding_amount`/`matched_funding_range` columns. Fails silently. |

### Source Tag

`"companyenrich-similar-preview"` on all core writes.

---

## Key Differences Between the Two Workflows

| | Firmo | Similar Preview |
|---|---|---|
| **Input** | 1 domain, 1 full payload | 1 input domain, 10 similar company profiles |
| **Payload source** | CompanyEnrich company lookup API | CompanyEnrich similar/preview API |
| **Extracted tables** | 12 breakout tables (prefixed `companyenrich_`) | 6 profile tables (prefixed `companyenrich_similar_company_`) + 1 similarity relationship table |
| **Core write strategy** | Writes unconditionally (upserts) | Writes only if domain is new to core (check-then-insert) |
| **Core tables touched** | 16 tables | 12 tables (attempted) |
| **Reference lookups** | employee_range, revenue, industry, technologies | employee_range, revenue, industry |
| **Technologies to core** | Yes (via `reference.technologies` -> `core.company_tech_on_site`) | No (extracted only) |
| **Funding rounds to core** | Yes (`core.company_funding_rounds`, `core.company_vc_investors`, `core.company_vc_backed`) | No (extracted only) |
| **Subsidiaries** | Yes | Not available in preview payload |
| **NAICS codes to core** | Yes | No (extracted only) |
| **Maturity** | Stable, production | Extracted tables working; core writes premature |

---

## Current Issues with Similar Preview Core Writes

### 1. Schema Mismatches (Silent Failures)

Two core writes fail silently because the code assumes column names that don't exist:

- **`core.company_business_model`**: Code writes `{ domain, business_model, source }`. Table actually has `{ domain, is_b2b, is_b2c }`. The derivation logic (scanning categories for "b2b"/"b2c" strings) is correct, but the output format is wrong.

- **`core.company_funding`**: Code writes `{ domain, total_funding, source }`. Table actually has `{ domain, source, raw_funding_range, raw_funding_amount, matched_funding_range }`. The firmo endpoint doesn't write to this table at all — it's populated by `company_discovery`.

### 2. Premature Core Writes

The core write logic was added before the extracted tables were validated. The extracted tables are now confirmed working (30 profiles, 30 locations, 28 socials, 372 technologies, 25 financial, 52 funding rounds). But the core writes were modeled after the firmo endpoint without fully auditing every target table's actual schema.

**Recommendation**: Strip the core writes out for now. Get the extracted layer solid, verify data quality, then add core writes back in deliberately — auditing each target table's actual columns and conflict strategies before wiring them up. The extracted tables are the source of truth; core writes are a coalescing convenience layer that should be added once we trust the data.

### 3. Things the Firmo Endpoint Does That Similar Preview Doesn't

Even when core writes are fixed, the similar preview endpoint is missing:

- **`core.company_tech_on_site`** — Firmo looks up/creates entries in `reference.technologies` then writes to core with `technology_id`. Similar preview only writes raw tech strings to its own extracted table.
- **`core.company_funding_rounds`** — Firmo writes individual rounds to core. Similar preview only writes to its own extracted funding rounds table.
- **`core.company_vc_investors`** / **`core.company_vc_backed`** — Firmo parses investor strings from funding rounds and writes individual investor records. Similar preview doesn't do this.
- **`core.company_naics_codes`** — Firmo writes to core. Similar preview only stores in extracted profile's `naics_codes` JSONB field.
- **`core.company_names`** — Firmo writes to this. Similar preview doesn't.
- **Location quality check** — Firmo compares incoming location field count against existing before overwriting. Similar preview does a simple upsert.

These gaps are fine for now — the similar preview data is lower-confidence (it's a free preview, not a paid enrichment), so being conservative about what goes to core makes sense.

---

## Verified Test Results (2026-02-05)

After deploying the updated similar preview endpoint:

**Extracted tables (all populated):**
| Table | Rows |
|---|---|
| `companyenrich_similar_company_profile` | 30 |
| `companyenrich_similar_company_location` | 30 |
| `companyenrich_similar_company_socials` | 28 |
| `companyenrich_similar_company_technologies` | 372 |
| `companyenrich_similar_company_financial` | 25 |
| `companyenrich_similar_company_funding_rounds` | 52 |

**Core dimension tables with source `companyenrich-similar-preview`:**
| Table | Rows | Notes |
|---|---|---|
| `core.company_descriptions` | 18 | Working |
| `core.company_locations` | 18 | Working |
| `core.company_employee_range` | 18 | Working |
| `core.company_revenue` | 18 | Working |
| `core.company_industries` | 18 | Working |
| `core.company_types` | 16 | Working (2 items had no type) |
| `core.company_social_urls` | 17 | Working |
| `core.company_categories` | 40 | Working |
| `core.company_keywords` | 413 | Working |
| `core.company_funding` | 0 | Schema mismatch — fails silently |
| `core.company_business_model` | 0 | Schema mismatch — fails silently |
