# infer_company_country

> **Last Updated:** 2026-01-29

## Purpose
Uses Gemini to infer company headquarters location (city, state, country) from name, domain, and LinkedIn URL.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-infer-company-country.modal.run
```

## Expected Payload
```json
{
  "company_name": "Stripe",
  "domain": "stripe.com",
  "company_linkedin_url": "https://linkedin.com/company/stripe"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_name | string | Yes | Company name |
| domain | string | No | Company domain |
| company_linkedin_url | string | No | LinkedIn company URL |

## Response
```json
{
  "success": true,
  "company_name": "Stripe",
  "city": "San Francisco",
  "state": "California",
  "country": "United States",
  "input_tokens": 52,
  "output_tokens": 18,
  "cost_usd": 0.0000124
}
```

| Field | Description |
|-------|-------------|
| city | Headquarters city (can be null) |
| state | Headquarters state/province (can be null) |
| country | Headquarters country (can be null) |
| input_tokens | Gemini input token count |
| output_tokens | Gemini output token count |
| cost_usd | Estimated API cost |

## How It Works
1. Sends company info to Gemini 3 Flash
2. Gemini returns JSON with city, state, country
3. Returns parsed location fields

## Model
`gemini-3-flash-preview`
