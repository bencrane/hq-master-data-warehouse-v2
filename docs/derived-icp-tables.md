# Derived ICP Tables

How we derive ICP (Ideal Customer Profile) data from a company's customers and case study champions.

---

## Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `derived.company_icp_industries_from_customers` | Industries of a company's customers | ~12,900 |
| `derived.icp_job_titles_from_champions` | Job titles of case study champions | ~15,100 |

---

## Data Flow: ICP Industries

```
core.company_customers (origin_company_domain → customer_domain)
        ↓
extracted.company_firmographics.matched_industry
        OR
extracted.company_discovery.industry
        ↓
(optional) reference.industry_lookup (normalize industry names)
        ↓
derived.company_icp_industries_from_customers
```

### Source Tables

1. **core.company_customers** - Links origin companies to their customers
   - `origin_company_domain`: The company we're building ICP for
   - `customer_domain`: Their customer's domain

2. **extracted.company_firmographics** - Firmographic data including industry
   - `company_domain`: Join key
   - `matched_industry`: Normalized industry (preferred)
   - `industry`: Raw industry

3. **extracted.company_discovery** - Discovery data including industry
   - `domain`: Join key
   - `industry`: Industry value

4. **reference.industry_lookup** - Industry normalization
   - `industry_raw`: Input industry name
   - `industry_cleaned`: Normalized output

### Refresh Query

```sql
INSERT INTO derived.company_icp_industries_from_customers (domain, icp_industry, customer_count)
SELECT
    cc.origin_company_domain as domain,
    COALESCE(
        il.industry_cleaned,
        cf.matched_industry,
        disco.industry
    ) as icp_industry,
    COUNT(DISTINCT cc.customer_domain) as customer_count
FROM core.company_customers cc
LEFT JOIN extracted.company_firmographics cf
    ON cc.customer_domain = cf.company_domain
LEFT JOIN extracted.company_discovery disco
    ON cc.customer_domain = disco.domain
LEFT JOIN reference.industry_lookup il
    ON COALESCE(cf.matched_industry, cf.industry, disco.industry) = il.industry_raw
WHERE cc.customer_domain IS NOT NULL
  AND COALESCE(cf.matched_industry, disco.industry) IS NOT NULL
GROUP BY 1, 2
ON CONFLICT (domain, icp_industry)
DO UPDATE SET
    customer_count = EXCLUDED.customer_count,
    updated_at = NOW();
```

---

## Data Flow: ICP Job Titles

```
core.company_customers (has case study URLs)
        ↓
extracted.case_study_details
        ↓
extracted.case_study_champions (or core.case_study_champions)
        ↓
derived.icp_job_titles_from_champions
```

### Source Tables

1. **core.company_customers** - Has `case_study_url` for some customers
2. **extracted.case_study_champions** - Champions extracted from case studies
   - `full_name`
   - `job_title`
3. **core.case_study_champions** - Consolidated champion data

### Refresh Query

```sql
INSERT INTO derived.icp_job_titles_from_champions (domain, job_title, champion_count)
SELECT
    csd.origin_company_domain as domain,
    csc.job_title,
    COUNT(*) as champion_count
FROM extracted.case_study_details csd
JOIN extracted.case_study_champions csc
    ON csd.id = csc.case_study_id
WHERE csc.job_title IS NOT NULL
  AND csc.job_title != ''
GROUP BY 1, 2
ON CONFLICT (domain, job_title)
DO UPDATE SET
    champion_count = EXCLUDED.champion_count,
    updated_at = NOW();
```

---

## Coverage Stats

As of 2026-02-14:

**ICP Industries:**
- 3,117 companies have ICP industry data
- 7,451 companies have customers total
- Gap: 4,334 companies need refresh or customer enrichment

**ICP Job Titles:**
- 1,152 companies have job title data
- Gap: 6,299 companies (many may not have case study champions)

---

## Blockers: Missing Customer Data

For ICP industries to work, we need industry data on customer companies.

**Current state:**
- 5,384 unique customer domains are NOT in firmographics or descriptions
- 105 origin companies have ZERO customers with industry data

**To enrich these customers:**
1. Get list of missing customer domains:
```sql
SELECT DISTINCT cc.customer_domain, cc.customer_name
FROM core.company_customers cc
LEFT JOIN core.company_descriptions cd ON cc.customer_domain = cd.domain
LEFT JOIN extracted.company_firmographics cf ON cc.customer_domain = cf.company_domain
WHERE cc.customer_domain IS NOT NULL
  AND cd.domain IS NULL
  AND cf.company_domain IS NULL;
```

2. Send to Clay/enrichment pipeline to get firmographics
3. Re-run ICP industries refresh

---

## Suggested Improvements

1. **Create refresh endpoint** - `POST /admin/derived/refresh-icp-industries`
2. **Add trigger-based refresh** - When new customers are added
3. **Track refresh timestamps** - Know when data was last updated
4. **Add confidence scores** - Weight by number of customers with data
