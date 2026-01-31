# upsert_core_company_full

> **Last Updated:** 2026-01-29

## Purpose
Accepts enriched company data and upserts to all core dimension tables in one call.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-upsert-core-company-full.modal.run
```

## Expected Payload
```json
{
  "company_name": "Stripe",
  "domain": "stripe.com",
  "linkedin_url": "https://linkedin.com/company/stripe",
  "industry": "Financial Services",
  "city": "San Francisco",
  "state": "California",
  "country": "United States",
  "employee_range": "5001-10000",
  "source": "gemini-enrichment"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_name | string | Yes | Company name |
| domain | string | Yes | Company domain (primary key) |
| linkedin_url | string | No | LinkedIn company URL |
| industry | string | No | Matched industry from reference.industry_lookup |
| city | string | No | Headquarters city |
| state | string | No | Headquarters state |
| country | string | No | Headquarters country |
| employee_range | string | No | Employee range (must match reference.employee_ranges) |
| source | string | No | Source identifier (default: "gemini-enrichment") |

## Response
```json
{
  "success": true,
  "domain": "stripe.com",
  "company_id": "uuid-here",
  "location_id": "uuid-here",
  "industry_id": "uuid-here",
  "employee_range_id": "uuid-here",
  "linkedin_url_id": "uuid-here"
}
```

## Tables Written
1. `core.companies` - domain, name, linkedin_url
2. `core.company_locations` - domain, city, state, country, source
3. `core.company_industries` - domain, matched_industry, source
4. `core.company_employee_ranges` - domain, matched_employee_range, source
5. `core.company_linkedin_urls` - domain, linkedin_url, source

## How It Works
1. Upserts to `core.companies` on domain conflict
2. If location data provided (city/state/country), upserts to `core.company_locations`
3. If industry provided, upserts to `core.company_industries`
4. If employee_range provided, upserts to `core.company_employee_ranges`
5. If linkedin_url provided, upserts to `core.company_linkedin_urls`

All upserts use domain as the conflict key (except employee_ranges which uses domain+source).
