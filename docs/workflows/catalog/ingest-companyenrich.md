# ingest_companyenrich

> **Last Updated:** 2026-02-04

## Purpose
Ingests company enrichment data from companyenrich.com. Stores raw payload, extracts to breakout tables, and coalesces to core tables. Single endpoint populates the full company profile across the database.

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
    "type": "private",
    "website": "https://harness.io",
    "revenue": "10m-50m",
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
  "core_company_inserted": true,
  "funding_rounds_processed": 8,
  "keywords_count": 26,
  "technologies_count": 22,
  "core_tech_on_site_count": 22,
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

### Core Tables (coalesced)
| Core Table | Data | Behavior |
|------------|------|----------|
| `core.companies` | name, domain, linkedin_url | Insert if not exists |
| `core.company_names` | raw_name, linkedin_url | Insert if domain+source not exists. Never overwrites cleaned_name |
| `core.company_employee_range` | matched range via `reference.employee_range_lookup` | Upsert (overwrites) |
| `core.company_revenue` | raw + matched range via `reference.revenue_range_lookup` | Upsert on domain+source |
| `core.company_types` | raw_type + matched_type (private→Private Company, etc.) | Upsert on domain+source |
| `core.company_locations` | city, state, country (pre-parsed) | Only overwrite if incoming has >= non-null fields |
| `core.company_descriptions` | description + seo_description as tagline | Upsert (overwrites) |
| `core.company_industries` | industry (singular) + insert to `reference.company_industries` | Insert if domain not exists |
| `core.company_tech_on_site` | each technology via `reference.technologies` (insert if new) | Upsert per tech |
| `core.company_keywords` | each keyword | Upsert per keyword |
| `core.company_categories` | each category | Upsert per category |
| `core.company_naics_codes` | each NAICS code | Upsert per code |
| `core.company_funding_rounds` | each funding round | Upsert per round |
| `core.company_vc_investors` | each parsed investor from funding `from` field | Upsert per investor |
| `core.company_vc_backed` | domain + vc_count (distinct investors) | Upsert |
| `core.company_social_urls` | all social URLs (linkedin, twitter, facebook, github, etc.) | Upsert (overwrites) |

## Reference Table Lookups

| Lookup | Raw Value Example | Matched Value |
|--------|-------------------|---------------|
| `reference.employee_range_lookup` | `1K-5K` → `1001-5000` | Upper-end mapping |
| `reference.revenue_range_lookup` | `10m-50m` → `$25M - $50M` | Upper-end mapping (conservative for ICP) |
| `reference.technologies` | Technology name | Insert if not found |
| `reference.company_industries` | Industry name | Insert if not found with source=companyenrich |

### Company Type Mapping (hardcoded)
| companyenrich | canonical |
|---------------|-----------|
| private | Private Company |
| public | Public Company |
| self-owned | Self-Employed |

## Design Decisions

**Dual Storage Pattern:** Arrays are kept in the main `companyenrich_company` table AND broken out into separate tables. This is intentional:
- Arrays in main table = easy retrieval when pulling a single company
- Breakout tables = enable querying/aggregating across companies (e.g., "all companies using Kubernetes")

Storage is cheap; query flexibility is valuable.

**Location overwrite protection:** Only overwrites `core.company_locations` if incoming data has more non-null fields (city/state/country) than existing. Prevents downgrading from a richer source.

**Industry insert-only:** Does not overwrite existing industry in `core.company_industries`. First source wins.

**Revenue upper-end mapping:** Companyenrich ranges don't map 1:1 to canonical ranges. Maps to upper end for conservative ICP filtering (rather miss on the high side than low).

## How It Works
1. Check/insert `core.companies` if domain not exists
2. Insert `core.company_names` if domain+source not exists
3. Look up and coalesce employee range, revenue, company type
4. Store raw payload to `raw.companyenrich_payloads`
5. Upsert flattened company data to `extracted.companyenrich_company`
6. Loop through all array fields → breakout tables + core tables
7. Parse funding rounds → extracted + core, extract individual investors → core VC tables
8. Coalesce location (with overwrite protection), description, industry, social URLs
9. Return counts of processed items

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

**Query across core tables (uses coalesced data):**
```sql
SELECT c.domain, c.name, er.employee_range, cl.country, ci.matched_industry
FROM core.companies c
LEFT JOIN core.company_employee_range er ON c.domain = er.domain
LEFT JOIN core.company_locations cl ON c.domain = cl.domain
LEFT JOIN core.company_industries ci ON c.domain = ci.domain
WHERE er.employee_range = '1001-5000' AND cl.country = 'United States';
```
