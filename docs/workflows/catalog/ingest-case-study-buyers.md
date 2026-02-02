# ingest_case_study_buyers

> **Last Updated:** 2026-01-29

## Purpose
Ingests case study buyer extraction results (from Gemini). Stores raw payload and explodes people array into individual rows.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-case-study-buyers.modal.run
```

## Expected Payload
```json
{
  "origin_company_name": "Hex",
  "origin_company_domain": "hex.tech",
  "case_study_url": "https://hex.tech/customers/toast",
  "customer_company_name": "Toast",
  "customer_company_domain": "toasttab.com",
  "people": [
    {
      "fullName": "John Smith",
      "jobTitle": "VP of Engineering"
    },
    {
      "fullName": "Jane Doe",
      "jobTitle": "Director of Data"
    }
  ],
  "success": true,
  "cost_usd": 0.000159,
  "input_tokens": 1250,
  "output_tokens": 85
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| origin_company_name | string | Yes | Company that published the case study |
| origin_company_domain | string | Yes | Publisher's domain |
| case_study_url | string | No | URL of the case study |
| customer_company_name | string | No | Featured customer company |
| customer_company_domain | string | No | Customer's domain |
| people | array | No | Array of people quoted |
| success, cost_usd, input_tokens, output_tokens | various | No | Gemini metadata (ignored but accepted) |

## Response
```json
{
  "success": true,
  "raw_id": "uuid-here",
  "buyer_count": 2
}
```

| Field | Description |
|-------|-------------|
| raw_id | ID of the raw payload record |
| buyer_count | Number of buyers extracted |

## Tables Written
- `raw.case_study_buyers_payloads` - stores full payload
- `extracted.case_study_buyers` - one row per person (exploded from people array)

## How It Works
1. Stores payload to `raw.case_study_buyers_payloads`
2. Loops through people array
3. For each person with a fullName, creates a row in `extracted.case_study_buyers`
4. Returns count of extracted buyers
