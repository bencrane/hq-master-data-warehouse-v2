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
  "customer_names": ["Resy", "GitHub", "..."],
  "confidence": "high"
}
```

## Tables Written

- **`raw.claygent_customers_structured_raw`** - Full payload storage
- **`extracted.claygent_customers_structured`** - One row per customer

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

## Tables Written

- **`raw.claygent_customers_structured_raw`** — Full payload storage
- **`extracted.claygent_customers_structured`** — One row per customer
- **`core.company_customers`** — Coalesced canonical table (source = `claygent_structured`)

## Notes

- Endpoint accepts raw `dict` (no Pydantic validation issues)
- Empty customers arrays handled gracefully
- Customers without `companyName` are skipped
- Case study URLs are stored but not automatically pushed to `staging.case_study_urls_to_process` (manual step for now)
