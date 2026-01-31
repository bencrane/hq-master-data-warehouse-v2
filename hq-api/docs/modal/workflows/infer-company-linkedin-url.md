# infer_company_linkedin_url

> **Last Updated:** 2026-01-29

## Purpose
Uses Gemini to infer company LinkedIn URL from name and domain.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-infer-company-linkedin-url.modal.run
```

## Expected Payload
```json
{
  "company_name": "Stripe",
  "domain": "stripe.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_name | string | Yes | Company name |
| domain | string | No | Company domain |

## Response
```json
{
  "success": true,
  "company_name": "Stripe",
  "linkedin_url": "https://www.linkedin.com/company/stripe",
  "input_tokens": 42,
  "output_tokens": 15,
  "cost_usd": 0.0000102
}
```

| Field | Description |
|-------|-------------|
| linkedin_url | LinkedIn company URL (null if cannot determine or invalid format) |
| input_tokens | Gemini input token count |
| output_tokens | Gemini output token count |
| cost_usd | Estimated API cost |

## How It Works
1. Sends company info to Gemini 3 Flash
2. Gemini returns LinkedIn URL guess
3. Validates URL starts with `https://www.linkedin.com/company/` or `https://linkedin.com/company/`
4. Returns null if format is invalid

## Model
`gemini-3-flash-preview`
