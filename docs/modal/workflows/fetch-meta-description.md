# fetch_meta_description

> **Last Updated:** 2026-01-29

## Purpose
Fetches a website and extracts the meta description tag. Zero API cost - just fetches HTML.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-fetch-meta-description.modal.run
```

## Expected Payload
```json
{
  "domain": "stripe.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| domain | string | Yes | Domain to fetch (without https://) |

## Response
```json
{
  "success": true,
  "domain": "stripe.com",
  "meta_description": "Stripe is a suite of APIs powering online payment processing...",
  "title": "Stripe | Payment Processing Platform for the Internet"
}
```

| Field | Description |
|-------|-------------|
| meta_description | Content from meta description tag (null if not found) |
| title | Page title (bonus field) |

## Error Response
```json
{
  "success": false,
  "error": "timeout",
  "domain": "example.com"
}
```

Possible errors: `timeout`, `connection_error`, `HTTP {status_code}`

## How It Works
1. Tries `https://{domain}`, falls back to `http://{domain}`
2. Fetches HTML with browser-like User-Agent
3. Extracts meta description from (in order):
   - `<meta name="description" content="...">`
   - `<meta property="og:description" content="...">`
   - `<meta name="twitter:description" content="...">`
4. Also extracts page `<title>` as bonus

## Cost
Zero API cost - just Modal compute time (~0.0001 cents per request)

## Timeout
30 seconds max, 10 second request timeout
