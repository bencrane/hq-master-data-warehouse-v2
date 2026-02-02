# update_staging_company_linkedin

> **Last Updated:** 2026-01-29

## Purpose
Updates company_linkedin_url and short_description fields on staging.companies_to_enrich records.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-update-staging-company-linkedin.modal.run
```

## Expected Payload
```json
{
  "domain": "stripe.com",
  "company_linkedin_url": "https://linkedin.com/company/stripe",
  "short_description": "Payment processing platform"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| domain | string | Yes | Domain to match (lookup key) |
| company_linkedin_url | string | No | LinkedIn URL to set |
| short_description | string | No | Description to set |

## Response
```json
{
  "success": true,
  "domain": "stripe.com",
  "updated_count": 1
}
```

| Field | Description |
|-------|-------------|
| updated_count | Number of rows updated (usually 1, 0 if domain not found) |

## Tables Written
- `staging.companies_to_enrich` - updates matching row by domain

## How It Works
1. Builds update object from non-null fields
2. Updates `staging.companies_to_enrich` WHERE domain = request.domain
3. Returns count of updated rows
