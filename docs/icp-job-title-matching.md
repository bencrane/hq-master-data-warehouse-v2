# ICP Job Title Matching System

## Overview

System for matching alumni of a company's customers to ICP-relevant job titles, and generating ICP job titles using AI.

---

## Modal Functions Created

### 1. `assess_icp_fit`
**Endpoint:** `POST https://bencrane--hq-master-data-ingest-assess-icp-fit.modal.run`

**Purpose:** Assess whether a job title is someone a company would sell to.

**Model:** Gemini 3 Flash

**Payload:**
```json
{
  "company_name": "SecurityPal AI",
  "company_domain": "securitypalhq.com",
  "company_description": "SecurityPal provides an assurance management platform...",
  "job_title": "Head of Security Engineering"
}
```

**Response:**
```json
{
  "verdict": "yes",
  "reason": "...",
  "jobTitle": "...",
  "companyName": "...",
  "inputTokens": 450,
  "outputTokens": 85,
  "costUsd": 0.000118
}
```

**Writes to:** `core.icp_verdicts` (upserts on `company_domain, job_title`)

---

### 2. `ingest_job_title_parsed`
**Endpoint:** `POST https://bencrane--hq-master-data-ingest-ingest-job-title-parsed.modal.run`

**Purpose:** Ingest raw job title → cleaned job title mappings into the canonical reference table.

**Payload:**
```json
{
  "raw_job_title": "VP of Security",
  "cleaned_job_title": "Vice President of Security",
  "seniority": "VP",
  "job_function": "Security",
  "source": "case-study-champions"
}
```

**Writes to:** `reference.job_title_parsed`

---

### 3. `compare_job_titles`
**Endpoint:** `POST https://bencrane--hq-master-data-ingest-compare-job-titles.modal.run`

**Purpose:** Compare a candidate job title against a list of job titles to determine if they represent the same role.

**Model:** Gemini 2.5 Flash

**Payload:**
```json
{
  "candidate_title": "Vice President of Security and Compliance",
  "job_title_list": ["CISO", "Head of Security", "VP Global Resilience and ERM"]
}
```

**Response:**
```json
{
  "success": true,
  "candidateTitle": "...",
  "anyMatches": true,
  "comparisons": [
    {
      "jobTitle": "...",
      "verdict": "SAME JOB" or "DIFFERENT JOB",
      "reasoning": "...",
      "jobTitleSameAs": "..."
    }
  ],
  "inputTokens": ...,
  "outputTokens": ...,
  "costUsd": ...
}
```

**Does NOT write to DB** - returns response only.

---

### 4. `parallel_icp_job_titles`
**Endpoint:** `POST https://bencrane--icp-titles.modal.run`

**Purpose:** Generate ICP job titles for a company using Parallel.ai Deep Research.

**Model:** Parallel.ai Ultra processor

**Timeout:** 30 minutes (Deep Research can take up to 25 min)

**Payload:**
```json
{
  "company_name": "Radar",
  "domain": "radar.com",
  "company_description": "Radar is the world's first Location OS..."
}
```

**Response:**
```json
{
  "success": true,
  "runId": "...",
  "companyName": "...",
  "domain": "...",
  "output": {
    "companyName": "...",
    "domain": "...",
    "inferredProduct": "...",
    "buyerPersona": "...",
    "titles": [
      {
        "title": "...",
        "buyerRole": "champion | evaluator | decision_maker",
        "reasoning": "..."
      }
    ]
  }
}
```

**Does NOT write to DB** - returns response only.

**TODO:** Add DB write, add wrapper at api.revenueinfra.com

---

## Database Tables

### `core.icp_verdicts`
Stores Gemini-assessed ICP fit verdicts.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| company_name | TEXT | Company name |
| company_domain | TEXT | Company domain |
| company_description | TEXT | Company description |
| job_title | TEXT | Job title assessed |
| verdict | TEXT | "yes" or "no" |
| reason | TEXT | AI reasoning |
| assessed_at | TIMESTAMPTZ | When assessed |

**Unique constraint:** `(company_domain, job_title)`

---

### `reference.job_title_parsed`
Canonical job title normalization lookup table.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| raw_job_title | TEXT | Raw job title (lookup key) |
| cleaned_job_title | TEXT | Normalized job title |
| seniority | TEXT | e.g., "VP", "Director" |
| job_function | TEXT | e.g., "Security", "Sales" |
| source | TEXT | e.g., "case-study-champions" |

---

## Data Flow

### Alumni Matching Pipeline

1. **Get company's customers** from `core.company_customers`
2. **Find alumni** of those customers in `core.person_work_history` (where `is_current = FALSE`)
3. **Get their current job** from `core.person_work_history` (where `is_current = TRUE`)
4. **Look up cleaned job title** by joining `title` to `reference.job_title_parsed.raw_job_title`
5. **Match against ICP titles** from `extracted.icp_job_titles` or case study champions

### Example Query: Alumni of SecurityPal's Customers with Cleaned Titles

```sql
WITH securitypal_customers AS (
    SELECT DISTINCT customer_domain
    FROM core.company_customers
    WHERE origin_company_domain = 'securitypalhq.com'
      AND customer_domain IS NOT NULL
)
SELECT DISTINCT ON (pwh.linkedin_url)
    pwh.linkedin_url,
    pwh.title AS raw_job_title,
    jtp.cleaned_job_title,
    cf.name AS origin_company_name,
    cd.domain AS origin_company_domain,
    cd.description AS origin_company_description
FROM core.person_work_history pwh
INNER JOIN securitypal_customers sc
    ON pwh.company_domain = sc.customer_domain
INNER JOIN reference.job_title_parsed jtp
    ON pwh.title = jtp.raw_job_title
CROSS JOIN core.company_descriptions cd
CROSS JOIN core.companies_full cf
WHERE pwh.is_current = FALSE
  AND cd.domain = 'securitypalhq.com'
  AND cf.domain = 'securitypalhq.com'
  AND jtp.cleaned_job_title IS NOT NULL
ORDER BY pwh.linkedin_url, pwh.start_date DESC NULLS LAST;
```

---

## Key Stats

### SecurityPal (`securitypalhq.com`)

- **21 customers** in `core.company_customers`
- **2,611 alumni** of those customers
- **92.8%** have matched job function or seniority
- **112 alumni** match the target ICP title list

### Champion Job Titles

- **374 companies** have case study champions
- **Median: 2** unique titles per company
- **67 companies** have 4+ unique titles
- **Top:** securitypalhq.com (19), gitlab.com (18), radar.com (15)

---

## ICP Job Title Sources

### 1. `extracted.icp_job_titles`
AI-generated ICP titles from Clay workflows.

Fields:
- `primary_titles` - Decision makers
- `influencer_titles` - Evaluators/champions
- `extended_titles` - Users/adjacent roles

### 2. `core.case_study_champions`
Actual job titles from case study contacts.

Fields:
- `job_title` - Raw title
- `matched_job_function` - Normalized function
- `matched_seniority` - Normalized seniority

### 3. `mapped.case_study_champions`
Mapped/normalized version with `matched_cleaned_job_title`.

---

## TODO

- [ ] Add DB write to `parallel_icp_job_titles`
- [ ] Add wrapper at `api.revenueinfra.com/icp-titles`
- [ ] Build backfill function to populate `matched_cleaned_job_title` for all case study champions
- [ ] Add cost tracking to `parallel_icp_job_titles` response
