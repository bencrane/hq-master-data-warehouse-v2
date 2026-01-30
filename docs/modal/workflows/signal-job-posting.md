# Signal: Job Posting

Detects new job postings at monitored companies.

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-signal-job-posting.modal.run
```

## Request Payload

```json
{
  "client_domain": "forethought.ai",
  "min_days_since_job_posting": 0,
  "max_days_since_job_posting": 60,
  "raw_job_post_data_payload": {...}
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `client_domain` | string | Client domain for multi-tenant tracking |
| `raw_job_post_data_payload` | object | Full payload from Clay |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `min_days_since_job_posting` | integer | Minimum days since posting (Clay filter setting) |
| `max_days_since_job_posting` | integer | Maximum days since posting (Clay filter setting) |

### jobPostData Fields

| Field | Type | Description |
|-------|------|-------------|
| `domain` | string | Company domain |
| `company_name` | string | Company name |
| `company_url` | string | Company LinkedIn URL |
| `company_id` | integer | LinkedIn company ID |
| `title` | string | Job title |
| `normalized_title` | string | Normalized job title |
| `seniority` | string | Seniority level (e.g., Director, VP) |
| `employment_type` | string | Employment type (Full-time, Part-time, etc.) |
| `location` | string | Job location |
| `url` | string | Job posting LinkedIn URL |
| `job_id` | integer | LinkedIn job ID |
| `posted_at` | string | ISO timestamp when job was posted |
| `salary_min` | number | Minimum salary |
| `salary_max` | number | Maximum salary |
| `salary_currency` | string | Salary currency (USD, etc.) |
| `salary_unit` | string | Salary unit (year, hour, etc.) |
| `recruiter_name` | string | Recruiter name |
| `recruiter_url` | string | Recruiter LinkedIn URL |

## Response

```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "company_domain": "claires.com",
  "job_title": "Head of Growth"
}
```

## Database Tables

### Raw Table: `raw.signal_job_posting_payloads`

Stores the full payload as received.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `client_domain` | TEXT | Client domain |
| `origin_table_id` | TEXT | Clay table ID |
| `origin_record_id` | TEXT | Clay record ID |
| `raw_payload` | JSONB | Full payload |
| `created_at` | TIMESTAMPTZ | When received |

### Extracted Table: `extracted.signal_job_posting`

Stores normalized/flattened fields for querying.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_payload_id` | UUID | Reference to raw payload |
| `client_domain` | TEXT | Client domain |
| `company_domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `company_linkedin_url` | TEXT | Company LinkedIn URL |
| `company_linkedin_id` | BIGINT | LinkedIn company ID |
| `job_title` | TEXT | Job title |
| `normalized_title` | TEXT | Normalized job title |
| `seniority` | TEXT | Seniority level |
| `employment_type` | TEXT | Employment type |
| `location` | TEXT | Job location |
| `job_linkedin_url` | TEXT | Job posting URL |
| `job_linkedin_id` | BIGINT | LinkedIn job ID |
| `posted_at` | TIMESTAMPTZ | When job was posted |
| `salary_min` | NUMERIC | Minimum salary |
| `salary_max` | NUMERIC | Maximum salary |
| `salary_currency` | TEXT | Salary currency |
| `salary_unit` | TEXT | Salary unit |
| `recruiter_name` | TEXT | Recruiter name |
| `recruiter_linkedin_url` | TEXT | Recruiter LinkedIn URL |
| `is_initial_check` | BOOLEAN | Initial check flag |
| `min_days_since_job_posting` | INTEGER | Min days filter (Clay setting) |
| `max_days_since_job_posting` | INTEGER | Max days filter (Clay setting) |
| `signal_detected_at` | TIMESTAMPTZ | When signal was detected |
| `created_at` | TIMESTAMPTZ | When record was created |

## Files

- Ingest: `modal-mcp-server/src/ingest/signal_job_posting_v2.py`
- Extraction: `modal-mcp-server/src/extraction/signal_job_posting_v2.py`
- Migration: `supabase/migrations/20260130_signal_job_posting.sql`
- Migration (recency): `supabase/migrations/20260130_signal_job_posting_recency.sql`

## Usage in Clay

1. Add HTTP endpoint action
2. Set URL to the endpoint above
3. Map fields from Clay to the request payload
4. Include `client_domain` for tracking
