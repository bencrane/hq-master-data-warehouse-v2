# ingest_companyenrich

> **Last Updated:** 2026-02-04

## Purpose
Ingests company enrichment data from companyenrich.com. Stores raw payload and extracts to main company table plus multiple breakout tables for querying across companies.

## Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-companyenrich.modal.run
```

**API Wrapper:**
```
POST https://api.revenueinfra.com/run/companies/companyenrich/ingest
```

## Expected Payload
```json
{
  "domain": "harness.io",
  "raw_payload": {
    "id": "abc123",
    "name": "Harness",
    "type": "Private",
    "website": "https://harness.io",
    "revenue": "$50M-$100M",
    "employees": "1K-5K",
    "industry": "Software",
    "industries": ["Software", "DevOps", "Cloud"],
    "description": "...",
    "seo_description": "...",
    "founded_year": 2017,
    "page_rank": 6,
    "logo_url": "https://...",
    "categories": ["DevOps", "CI/CD"],
    "keywords": ["continuous delivery", "devops", "kubernetes"],
    "technologies": ["Google-Analytics", "Cloudflare-Cdn", "Wordpress"],
    "naics_codes": ["511210", "541511"],
    "location": {
      "address": "123 Main St",
      "phone": "+1-555-1234",
      "postal_code": "94105",
      "city": {"id": 123, "name": "San Francisco", "latitude": 37.77, "longitude": -122.41},
      "state": {"id": 5, "name": "California", "code": "CA"},
      "country": {"name": "United States", "code": "US"}
    },
    "socials": {
      "linkedin_url": "https://linkedin.com/company/harnessinc",
      "linkedin_id": "12345678",
      "twitter_url": "https://twitter.com/harnessio",
      "facebook_url": "...",
      "github_url": "...",
      "youtube_url": "...",
      "instagram_url": "...",
      "crunchbase_url": "...",
      "g2_url": "...",
      "angellist_url": "..."
    },
    "financial": {
      "total_funding": 737700000,
      "funding_stage": "debt_financing",
      "funding_date": "2024-01-15T00:00:00Z",
      "stock_symbol": null,
      "stock_exchange": null,
      "funding": [
        {
          "date": "2021-01-14T00:00:00Z",
          "type": "Series C",
          "amount": "85000000 USD",
          "from": "Alkeon Capital",
          "url": "..."
        }
      ]
    },
    "subsidiaries": [
      {"name": "SubCo", "domain": "subco.com"}
    ],
    "updated_at": "2024-12-01T00:00:00Z"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| domain | string | Yes | Company domain (primary key for upserts) |
| raw_payload | object | Yes | Full companyenrich.com response |

## Response
```json
{
  "success": true,
  "raw_id": "uuid-here",
  "extracted_id": "uuid-here",
  "funding_rounds_processed": 8,
  "keywords_count": 26,
  "technologies_count": 22,
  "investors_count": 8
}
```

## Tables Written

### Raw Storage
- `raw.companyenrich_payloads` - Full JSON payload

### Extracted - Main Table
- `extracted.companyenrich_company` - Flattened company data with arrays for easy single-company retrieval

### Extracted - Breakout Tables (for cross-company queries)
| Table | Key | Purpose |
|-------|-----|---------|
| `companyenrich_keywords` | domain, keyword | Query companies by keyword |
| `companyenrich_technologies` | domain, technology | Query companies by tech stack |
| `companyenrich_industries` | domain, industry | Query companies by industry |
| `companyenrich_categories` | domain, category | Query companies by category |
| `companyenrich_naics_codes` | domain, naics_code | Query companies by NAICS |
| `companyenrich_funding_rounds` | domain, funding_date, funding_type | All funding rounds |
| `companyenrich_investors` | domain, investor_name | Unique investors per company |
| `companyenrich_vc_investments` | domain, investor_name, funding_date, funding_type | Investor + round details |
| `companyenrich_socials` | domain | Social media URLs |
| `companyenrich_location` | domain | Location details |
| `companyenrich_subsidiaries` | domain, subsidiary_name | Company subsidiaries |

## Design Decisions

**Dual Storage Pattern:** Arrays are kept in the main `companyenrich_company` table AND broken out into separate tables. This is intentional:
- Arrays in main table = easy retrieval when pulling a single company
- Breakout tables = enable querying/aggregating across companies (e.g., "all companies using Kubernetes")

Storage is cheap; query flexibility is valuable.

## How It Works
1. Stores raw payload to `raw.companyenrich_payloads`
2. Upserts flattened company data to `extracted.companyenrich_company`
3. Loops through all array fields and upserts to breakout tables
4. Parses funding rounds and extracts individual investors
5. Returns counts of processed items

## Example Queries

**Find all companies using a specific technology:**
```sql
SELECT c.domain, c.name, c.employees
FROM extracted.companyenrich_company c
JOIN extracted.companyenrich_technologies t ON c.domain = t.domain
WHERE t.technology = 'Kubernetes';
```

**Find all companies with a specific investor:**
```sql
SELECT c.domain, c.name, i.funding_type, i.amount
FROM extracted.companyenrich_company c
JOIN extracted.companyenrich_vc_investments i ON c.domain = i.domain
WHERE i.investor_name = 'Sequoia';
```
