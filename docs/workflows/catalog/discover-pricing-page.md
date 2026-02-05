# discover_pricing_page_url

> **Last Updated:** 2026-02-05

## Purpose
Uses Gemini to discover a company's pricing page URL by analyzing their homepage and finding pricing-related links. This is useful when you only have a domain and need to find the pricing page URL.

## Endpoints

**Modal (internal):**
```
POST https://bencrane--hq-master-data-ingest-discover-pricing-page-url.modal.run
```

**Railway API (frontend-facing):**
```
POST https://api.revenueinfra.com/api/companies/discover-pricing-page
```

## Expected Payload
```json
{
  "domain": "stripe.com",
  "company_name": "Stripe"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| domain | string | Yes | Company domain (e.g., "stripe.com") |
| company_name | string | No | Company name (helps with context) |

## Response
```json
{
  "success": true,
  "domain": "stripe.com",
  "raw_payload_id": "uuid",
  "pricing_page_url": "https://stripe.com/pricing",
  "confidence": "high",
  "explanation": "Found 'Pricing' link in main navigation pointing to /pricing"
}
```

| Field | Description |
|-------|-------------|
| success | Whether the operation succeeded |
| domain | Normalized domain |
| raw_payload_id | ID of raw payload record |
| pricing_page_url | Discovered pricing page URL (null if not found) |
| confidence | Confidence level: "high", "medium", or "low" |
| explanation | Why the URL was chosen or why none was found |

## How It Works
1. Fetches the company homepage
2. Extracts all links with their anchor text
3. Sends links + page content to Gemini
4. Gemini analyzes and identifies the pricing page link
5. Returns URL with confidence level
6. Auto-upserts to `core.ancillary_urls` for high/medium confidence results

## Model
`gemini-2.0-flash`

## Tables Used
- `raw.discover_pricing_page_payloads` (write - stores raw request)
- `extracted.discover_pricing_page` (write - stores discovered URL + confidence)
- `core.ancillary_urls` (upsert - stores pricing_page_url if high/medium confidence)

## Data Flow
```
Request -> raw.discover_pricing_page_payloads -> extracted.discover_pricing_page -> core.ancillary_urls
```

## Confidence Levels

| Level | Meaning | Action |
|-------|---------|--------|
| high | Clear pricing link found (e.g., "Pricing" text, /pricing URL) | Upserted to core |
| medium | Likely pricing page but not certain | Upserted to core |
| low | Could not find pricing page or uncertain | NOT upserted to core |

## Error Cases

| Error | Cause |
|-------|-------|
| "No domain provided" | Missing domain in payload |
| "Failed to fetch homepage: HTTP {status}" | Homepage not accessible |
| "Homepage fetch timeout" | Homepage took too long to load |
| "Homepage connection error" | Could not connect to domain |
