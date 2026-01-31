# ingest_company_customers_structured

> **Last Updated:** 2026-01-31

## Purpose
Ingests structured company customers data from Clay webhooks. Accepts flat payload with customers array containing company names, URLs, and case study flags.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-company-customers-85468a.modal.run
```

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

## Notes

- Endpoint accepts raw `dict` (no Pydantic validation issues)
- Empty customers arrays handled gracefully
- Customers without `companyName` are skipped
- Data should be coalesced to `core.company_customers` for the status endpoint to work
