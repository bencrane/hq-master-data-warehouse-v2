# infer_company_industry

> **Last Updated:** 2026-01-29

## Purpose
Uses Gemini to infer company industry from name, domain, and description. Matches against `reference.industry_lookup` to return a normalized industry.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-infer-company-industry.modal.run
```

## Expected Payload
```json
{
  "company_name": "Stripe",
  "domain": "stripe.com",
  "short_description": "Online payment processing for internet businesses"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_name | string | Yes | Company name |
| domain | string | No | Company domain |
| short_description | string | No | Brief company description |

## Response
```json
{
  "success": true,
  "company_name": "Stripe",
  "gemini_raw": ["Financial Services", "Payment Processing", "FinTech"],
  "matched_industries": [
    {
      "gemini_guess": "Financial Services",
      "matched_industry": "Financial Services",
      "match_type": "exact"
    }
  ],
  "best_match": "Financial Services",
  "input_tokens": 45,
  "output_tokens": 12,
  "cost_usd": 0.0000093
}
```

| Field | Description |
|-------|-------------|
| gemini_raw | Raw industry guesses from Gemini |
| matched_industries | Each guess matched against reference.industry_lookup |
| best_match | First non-null matched industry from your DB |
| input_tokens | Gemini input token count |
| output_tokens | Gemini output token count |
| cost_usd | Estimated API cost |

## How It Works
1. Sends company info to Gemini 3 Flash
2. Gemini returns up to 3 industry guesses
3. Each guess is matched against `reference.industry_lookup` via exact match, then fuzzy match on keywords
4. Returns best matching industry from your normalized list

## Model
`gemini-3-flash-preview`

## Tables Used
- `reference.industry_lookup` (read - for matching)
