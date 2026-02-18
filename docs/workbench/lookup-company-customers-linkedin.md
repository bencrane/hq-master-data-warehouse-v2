# Objective: Add LinkedIn URL to lookup_company_customers Endpoint

## Goal
Enhance the `lookup_company_customers` Modal endpoint to return the customer's LinkedIn URL alongside existing fields.

## Endpoint
- **Modal URL:** `https://bencrane--hq-master-data-ingest-lookup-company-customers.modal.run`
- **File:** `/modal-functions/src/ingest/lookup_company_customers.py`

## Current State
- Endpoint updated to fetch LinkedIn URLs from `core.companies_full` table
- Code is ready but Modal may be caching old version
- Need to deploy and verify

## Data Sources
- **Customers:** `core.company_customers` (has `customer_domain`)
- **LinkedIn URLs:** `core.companies_full` (has `domain` and `linkedin_url`)

## Expected Response
```json
{
  "success": true,
  "domain": "salesforce.com",
  "customer_count": 5,
  "customers": [
    {
      "origin_company_name": "Salesforce",
      "origin_company_domain": "salesforce.com",
      "customer_name": "Acme Corp",
      "customer_domain": "acme.com",
      "customer_linkedin_url": "https://linkedin.com/company/acme"
    }
  ]
}
```

## Next Steps
1. Deploy: `cd modal-functions && uv run modal deploy src/app.py`
2. Test: `curl -X POST "https://bencrane--hq-master-data-ingest-lookup-company-customers.modal.run" -H "Content-Type: application/json" -d '{"domain":"salesforce.com"}'`
3. Verify `customer_linkedin_url` field is populated
