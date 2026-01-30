# extract_case_study_buyer

> **Last Updated:** 2026-01-29

## Purpose
Uses Gemini to extract buyer/champion information from a case study URL. Returns customer company details and people quoted.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-extract-case-study-buyer.modal.run
```

## Expected Payload
```json
{
  "origin_company_name": "Hex",
  "origin_company_domain": "hex.tech",
  "customer_company_name": "Toast",
  "case_study_url": "https://hex.tech/customers/toast"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| origin_company_name | string | Yes | Company that published the case study |
| origin_company_domain | string | Yes | Publisher's domain |
| customer_company_name | string | Yes | Featured customer company |
| case_study_url | string | Yes | URL of the case study page |

## Response
```json
{
  "success": true,
  "customer_company_name": "Toast",
  "customer_company_domain": "toasttab.com",
  "people": [
    {
      "fullName": "John Smith",
      "jobTitle": "VP of Engineering"
    }
  ],
  "input_tokens": 1250,
  "output_tokens": 85,
  "cost_usd": 0.000159
}
```

| Field | Description |
|-------|-------------|
| customer_company_name | Customer company name from case study |
| customer_company_domain | Inferred customer domain |
| people | Array of people quoted in the case study |
| input_tokens | Gemini input token count |
| output_tokens | Gemini output token count |
| cost_usd | Estimated API cost |

## How It Works
1. Sends case study URL to Gemini 3 Flash
2. Gemini navigates to the URL and extracts:
   - Customer company name
   - Customer company domain
   - All people quoted with names and job titles
3. Returns structured data

## Model
`gemini-3-flash-preview`

## Note
The response from this endpoint is typically sent to `ingest_case_study_buyers` for storage.
