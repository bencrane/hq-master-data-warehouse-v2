# ingest_company_customers_structured

> **Last Updated:** 2026-02-04

## Purpose
Ingests structured company customers data from Clay webhooks. Accepts flat payload with customers array containing company names, URLs, and case study flags.

**This is the canonical "get customers of" ingest endpoint.** All other variants (customers-of-1, customers-of-2, customers-of-4) are deprecated.

## Endpoint
```
POST https://api.revenueinfra.com/run/companies/claygent/customers-of-3/ingest
```

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-ingest-company-customers-85468a.modal.run
```

## Deprecated Endpoints (do not use)
- `customers-of-1` — old Claygent format
- `customers-of-2` — different payload shape
- `customers-of-4` — comma-separated customer names

## Expected Payload (Flat Structure)

```json
{
  "origin_company_domain": "andela.com",
  "origin_company_name": "Andela",
  "response": "Summary text of customer research...",
  "customers": [
    {
      "url": "https://www.andela.com/customer-stories/resy",
      "companyName": "Resy",
      "hasCaseStudy": true
    },
    {
      "url": "",
      "companyName": "GitHub",
      "hasCaseStudy": false
    }
  ],
  "reasoning": "Explanation of how customers were identified...",
  "confidence": "high",
  "stepsTaken": ["url1", "url2"]
}
```

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| origin_company_domain | string | Yes | Domain of company whose customers are being researched |
| origin_company_name | string | No | Name of the origin company |
| response | string | No | Text summary of customer research |
| customers | array | No | Array of customer objects |
| reasoning | string | No | Explanation of identification process |
| confidence | string | No | Confidence level (high/medium/low) |
| stepsTaken | array | No | URLs visited during research |

### Customer Object

| Field | Type | Description |
|-------|------|-------------|
| companyName | string | Name of the customer company |
| url | string | Case study URL (empty string if none) |
| hasCaseStudy | boolean | Whether a case study exists |

## Response

```json
{
  "success": true,
  "raw_id": "uuid-here",
  "domain": "andela.com",
  "customers_extracted": 19,
  "customers_to_core": 19,
  "staging_case_study_urls": 12,
  "customer_names": ["Resy", "GitHub", "..."],
  "confidence": "high"
}
```

## Tables Written

| Table | Purpose |
|-------|---------|
| `raw.claygent_customers_structured_raw` | Full payload storage |
| `extracted.claygent_customers_structured` | One row per customer |
| `core.company_customers` | Coalesced canonical table (source = `claygent_structured`) |
| `raw.staging_case_study_urls` | Case study URLs queued for Gemini extraction |

## Domain Normalization

The ingest function normalizes `origin_company_domain` before writing to any table:
- Strips `https://` and `http://`
- Strips trailing `/` and any path
- Strips `www.` prefix
- Lowercases

Example: `www.hubspot.com/customers/` → `hubspot.com`

**File:** `company_customers_structured.py:normalize_domain()`

## Clay Webhook Setup

Map each Claygent output field separately:

| Clay Column | Webhook Field |
|-------------|---------------|
| Normalized URL | `origin_company_domain` |
| Company Name | `origin_company_name` |
| Claygent.Response | `response` |
| Claygent.Customers | `customers` |
| Claygent.Reasoning | `reasoning` |
| Claygent.Confidence | `confidence` |
| Claygent.Steps Taken | `stepsTaken` |

## Downstream: Sending Case Study URLs to Clay

After ingesting customers, case study URLs are staged in `raw.staging_case_study_urls`. To send them to a Clay webhook for Gemini extraction:

```
POST https://api.revenueinfra.com/run/case-study-urls/to-clay
```
```json
{
  "webhook_url": "https://api.clay.com/v3/sources/webhook/...",
  "batch_id": "2026-02-04-companyenrich"
}
```

This proxies to Modal function `send_case_study_urls_to_clay` which sends at 10 records/second and marks each row `sent_to_clay = true`.

## Downstream: Check If Case Study Already Extracted

```
POST https://api.revenueinfra.com/run/companies/case-study-details/lookup
```
```json
{
  "case_study_url": "https://www.andela.com/customer-stories/resy"
}
```

Returns `{ "exists": true/false }` — checks `extracted.case_study_details` by `case_study_url`.

## Known Issues (2026-02-04)

### origin_company_name null in staging table
When the ingest function upserts to `raw.staging_case_study_urls` with `on_conflict="case_study_url"`, rows that already existed (from older pipeline migration) may not get `origin_company_name` updated. Root cause not fully diagnosed. 1,040 rows were sent to Clay with null `origin_company_name`. Backfilled from `core.company_customers` and `core.companies` but 26 remain null. **This needs a proper fix — either validate data before sending to Clay, or confirm the Supabase upsert actually updates all columns on conflict.**

### Domain normalization was retrofitted
10,982 dirty `origin_company_domain` values (www. prefix, trailing slashes, paths) were cleaned up in `core.company_customers` on 2026-02-04. 7,336 were duplicates (deleted), 3,646 were updated. 1,861 cleaned in `raw.staging_case_study_urls`. Normalization function added to prevent recurrence.

## Notes

- Endpoint accepts raw `dict` (no Pydantic validation issues)
- Empty customers arrays handled gracefully
- Customers without `companyName` are skipped
