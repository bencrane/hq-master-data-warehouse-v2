# Staffing Parallel AI Tables

This document describes the tables used for storing Parallel AI search results for staffing/recruiting research.

**Migration:** `supabase/migrations/20260206_staffing_parallel_ai_tables.sql`

## Table Versioning

We're iterating on the Parallel AI output format. Tables are versioned (v1, v2, etc.) until we settle on a final structure.

---

## V1 Tables - Structured Job Search Output

These tables store the **structured output** from Parallel AI's web interface (not the raw API response).

### Source Format

The input is a JSON with:
```json
{
  "input": "{ original search request }",
  "output": {
    "market_overview": "...",
    "key_skill_trends": [...],
    "job_postings": [...]
  }
}
```

---

### raw.staffing_parallel_job_search_v1_payloads

Full JSON payload storage.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| search_name | text | Optional identifier (e.g., "devops-sre-jan2026") |
| input_objective | text | The objective from the search |
| input_queries | text[] | The search queries used |
| payload | jsonb | Full JSON response |
| created_at | timestamptz | When stored |

---

### extracted.staffing_parallel_job_search_v1

Search-level metadata and market overview.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| raw_payload_id | uuid | FK to raw payload |
| search_name | text | Optional identifier |
| market_overview | text | Market analysis text |
| job_posting_count | int | Number of job postings found |
| skill_trend_count | int | Number of skill trends identified |
| created_at | timestamptz | When extracted |

---

### extracted.staffing_parallel_job_postings_v1

Individual job postings extracted from search.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| search_id | uuid | FK to parent search |
| company_name | text | e.g., "Life360" |
| job_title | text | e.g., "Staff DevOps Engineer" |
| location | text | e.g., "Remote, USA" |
| salary_range | text | e.g., "$163,500 to $269,000" |
| equity_offered | boolean | Whether equity is mentioned |
| key_responsibilities | text | Quoted responsibilities from posting |
| required_technologies | text | e.g., "CI/CD, Jenkins, Kubernetes" |
| experience_level | text | e.g., "Staff", "Senior", "Lead" |
| posting_url | text | Direct link to job posting |
| created_at | timestamptz | When extracted |

---

### extracted.staffing_parallel_skill_trends_v1

Skill trends identified in the market.

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| search_id | uuid | FK to parent search |
| skill_category | text | e.g., "Containerization and Orchestration" |
| technologies | text | e.g., "Kubernetes, Amazon EKS" |
| description | text | Explanation of the trend |
| created_at | timestamptz | When extracted |

---

## Other Tables (API Response Format)

### raw.staffing_parallel_search_payloads / extracted.staffing_parallel_search

These tables store the **raw API response** format from the `/search` endpoint, which has a different structure:
- `results[]` with `url`, `title`, `excerpts[]`
- No structured extraction of job postings

Use V1 tables above for structured job data.

---

## Data Flow

```
Parallel AI Web UI
       ↓
  JSON export
       ↓
raw.staffing_parallel_job_search_v1_payloads
       ↓
extracted.staffing_parallel_job_search_v1 (market overview)
       ↓
  ├── extracted.staffing_parallel_job_postings_v1 (individual jobs)
  └── extracted.staffing_parallel_skill_trends_v1 (skill trends)
```

---

## Ingest Endpoints

### API Response Format (raw search results)

**HQ API:**
```
POST https://api.revenueinfra.com/api/companies/ingest-staffing-parallel-search
```

**Modal Direct:**
```
POST https://bencrane--hq-master-data-ingest-ingest-staffing-parallel-search.modal.run
```

**Payload:** Full response from `search-parallel-ai` endpoint:
```json
{
  "domain": "example.com",
  "success": true,
  "company_name": "Example Inc",
  "parallel_response": {
    "usage": [...],
    "results": [...],
    "search_id": "..."
  }
}
```

Stores to: `raw.staffing_parallel_search_payloads` → `extracted.staffing_parallel_search`

---

### V1 Structured Job Search Format

TBD - Endpoint to be created for ingesting structured job search JSON exports from Parallel AI web UI.
