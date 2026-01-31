# Target Client Views - ICP-Based Lead Filtering

## Overview

System for generating shareable lead views based on a company's ICP (Ideal Customer Profile) data.

## Use Cases

1. **Demo Flow (Loom videos)**: Enter domain on pre-page, review ICP specs, click "Go" to load leads dashboard with filters applied
2. **Shareable Links**: Auto-generate saved views for companies, share via slug-based URLs

## Data Sources

| Data | Table | Key Fields |
|------|-------|------------|
| Company Name | `core.companies` | `name`, `cleaned_name` |
| Customer Domains | `core.company_customers` | `customer_domain` |
| ICP Industries | `extracted.icp_industries` | `matched_industries` (normalized against canonical) |
| ICP Job Titles | `extracted.icp_job_titles` | `primary_titles`, `influencer_titles`, `extended_titles` (cleaned from camelCase) |
| Value Proposition | `extracted.icp_value_proposition` | `value_proposition`, `core_benefit`, `target_customer`, `key_differentiator` |

## Saved Views Table

**Table:** `core.target_client_views`

| Column | Type | Description |
|--------|------|-------------|
| domain | text | Target company domain (unique) |
| name | text | Company name |
| slug | text | URL-friendly identifier (unique) |
| filters | jsonb | Filter configuration |
| endpoint | text | Default: `/api/leads` |

## API Endpoints

### 1. Lookup Company ICP

**Endpoint:** `https://bencrane--hq-master-data-ingest-lookup-company-icp.modal.run`

**Purpose:** Fetch all ICP data for a domain (used by dashboard on page load)

**Payload:**
```json
{
  "domain": "securitypalhq.com"
}
```

**Response:**
```json
{
  "success": true,
  "domain": "securitypalhq.com",
  "company_name": "SecurityPal",
  "customer_domains": ["mongodb.com", "openai.com", "plaid.com", ...],
  "icp_industries": ["Computer & Network Security", ...],
  "icp_job_titles": {
    "primary_titles": ["Chief Information Security Officer", ...],
    "influencer_titles": [...],
    "extended_titles": [...]
  },
  "value_proposition": {
    "value_proposition": "...",
    "core_benefit": "...",
    "target_customer": "...",
    "key_differentiator": "..."
  }
}
```

### 2. Create Target Client View

**Endpoint:** `https://bencrane--hq-master-data-ingest-create-target-client-view.modal.run`

**Purpose:** Auto-generate and save a view for sharing

**Payload:**
```json
{
  "domain": "securitypalhq.com",
  "slug": "securitypal"  // optional, auto-generated if not provided
}
```

**Response:**
```json
{
  "success": true,
  "view_id": "uuid",
  "domain": "securitypalhq.com",
  "company_name": "SecurityPal",
  "slug": "securitypal",
  "shareable_url": "/leads?view=securitypal",
  "filters": {
    "customer_domains": [...],
    "icp_industries": [...],
    "icp_job_titles": [...]
  }
}
```

## Frontend URL Patterns

| Pattern | Use Case |
|---------|----------|
| `/leads?target=securitypalhq.com` | Live ICP data fetch (demo flow) |
| `/leads?view=securitypal` | Load saved view from DB |

## Frontend Flow

### Demo Flow (Pre-Page)

1. User enters domain on pre-page
2. Pre-page displays:
   - ICP industries (as badges)
   - ICP job titles (as badges)
   - Customer companies list
3. User clicks "Find People" / "Go"
4. Navigates to `/leads?target=securitypalhq.com`
5. Dashboard calls `lookup_company_icp`
6. Populates card badges with ICP specs
7. Applies filters to leads table

### Saved View Flow

1. Call `create_target_client_view` with domain
2. Get back slug and shareable URL
3. Share `/leads?view=securitypal`
4. Dashboard loads filters from `core.target_client_views`

## Related ICP Ingestion Endpoints

| Endpoint | Purpose |
|----------|---------|
| `ingest-icp-industries` | Ingest + GPT-4o-mini matching to canonical industries |
| `ingest-icp-job-titles` | Ingest + camelCase normalization |
| `ingest-icp-value-proposition` | Ingest value prop data |
| `ingest-icp-fit-criterion` | Ingest fit criterion data |
