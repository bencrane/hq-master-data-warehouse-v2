# infer_company_employee_range

> **Last Updated:** 2026-01-29

## Purpose
Uses Gemini to estimate company employee count and classify into standard employee ranges.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-infer-company-employee-range.modal.run
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
  "employee_range": "5001-10000",
  "input_tokens": 65,
  "output_tokens": 8,
  "cost_usd": 0.0000097
}
```

| Field | Description |
|-------|-------------|
| employee_range | One of the standard ranges (or null if cannot determine) |
| input_tokens | Gemini input token count |
| output_tokens | Gemini output token count |
| cost_usd | Estimated API cost |

## Standard Ranges
- `1-10`
- `11-50`
- `51-100`
- `101-250`
- `251-500`
- `501-1000`
- `1001-5000`
- `5001-10000`
- `10001+`

## How It Works
1. Sends company info to Gemini 3 Flash along with list of valid ranges
2. Gemini returns one of the exact ranges
3. Validates response is one of the allowed ranges
4. Returns null if Gemini returns something outside the ranges

## Model
`gemini-3-flash-preview`
