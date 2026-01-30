# ingest_cb_vc_portfolio

> **Last Updated:** 2026-01-29

## Purpose
Ingests Crunchbase VC portfolio company data. Stores raw payload and explodes VC columns into individual rows.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-cb-vc-portfolio.modal.run
```

## Expected Payload
```json
{
  "company_name": "Acme Corp",
  "domain": "acme.com",
  "city": "San Francisco",
  "state": "California",
  "country": "United States",
  "short_description": "B2B SaaS platform",
  "employee_range": "51-100",
  "last_funding_date": "2024-03-15",
  "last_funding_type": "Series B",
  "last_funding_amount": "50000000",
  "last_equity_funding_type": "Series B",
  "last_leadership_hiring_date": "2024-01-10",
  "founded_date": "2020-01-01",
  "estimated_revenue_range": "$10M-$50M",
  "funding_status": "Late Stage Venture",
  "total_funding_amount": "75000000",
  "total_equity_funding_amount": "75000000",
  "operating_status": "Active",
  "company_linkedin_url": "https://linkedin.com/company/acme",
  "vc": "Sequoia",
  "vc1": "a16z",
  "vc2": "Greylock",
  "vc3": null,
  "vc4": null,
  "vc5": null,
  "vc6": null,
  "vc7": null,
  "vc8": null,
  "vc9": null,
  "vc10": null,
  "vc11": null,
  "vc12": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| company_name | string | Yes | Company name |
| domain | string | No | Company domain |
| vc, vc1-vc12 | string | No | VC investor names (up to 13 VCs) |
| All other fields | string | No | Various company/funding metadata |

## Response
```json
{
  "success": true,
  "raw_id": "uuid-here",
  "vc_count": 3
}
```

| Field | Description |
|-------|-------------|
| raw_id | ID of the raw payload record |
| vc_count | Number of VCs extracted (non-null vc fields) |

## Tables Written
- `raw.cb_vc_portfolio_payloads` - stores full payload as-is
- `extracted.cb_vc_portfolio` - one row per VC (exploded from vc columns)

## How It Works
1. Stores all fields to `raw.cb_vc_portfolio_payloads`
2. Loops through vc, vc1, vc2... vc12 columns
3. For each non-null VC, creates a row in `extracted.cb_vc_portfolio` with all company data + that VC name
4. Returns count of extracted VC rows
