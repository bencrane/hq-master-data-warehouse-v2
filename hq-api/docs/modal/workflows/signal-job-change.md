# Signal: Job Change

Detects when a person changes companies.

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-signal-job-change.modal.run
```

## Request Payload

```json
{
  "client_domain": "forethought.ai",
  "raw_job_change_payload": {...}
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `client_domain` | string | Client domain for multi-tenant tracking |
| `raw_job_change_payload` | object | Full payload from Clay |

## Response

```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "person_name": "Courtney Graybill",
  "new_company_domain": "kohls.com"
}
```

## Extracted Fields

From the raw payload, we extract:

**Person Info:**
- `person_name` - Full name
- `person_first_name`, `person_last_name`
- `person_linkedin_url`, `person_linkedin_slug`
- `person_title` - Current title
- `person_headline`
- `person_location`, `person_country`

**New Company (from `fullProfile.latest_experience`):**
- `new_company_domain`
- `new_company_name`
- `new_company_linkedin_url`
- `new_job_title`
- `new_job_start_date`
- `new_job_location`

**Previous Company:**
- `previous_company_linkedin_url`

**Confidence:**
- `confidence` - Score (0-100)
- `reduced_confidence_reasons` - Array of reasons if confidence reduced

## Database Tables

### Raw Table: `raw.signal_job_change_payloads`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `client_domain` | TEXT | Client domain |
| `origin_table_id` | TEXT | Clay table ID |
| `origin_record_id` | TEXT | Clay record ID |
| `raw_payload` | JSONB | Full payload |
| `created_at` | TIMESTAMPTZ | When received |

### Extracted Table: `extracted.signal_job_change`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_payload_id` | UUID | Reference to raw |
| `client_domain` | TEXT | Client domain |
| `person_name` | TEXT | Full name |
| `person_linkedin_url` | TEXT | LinkedIn URL |
| `new_company_domain` | TEXT | New company domain |
| `new_company_name` | TEXT | New company name |
| `new_job_title` | TEXT | New job title |
| `new_job_start_date` | DATE | Job start date |
| `confidence` | INTEGER | Confidence score |
| `is_initial_check` | BOOLEAN | Initial check flag |
| `signal_detected_at` | TIMESTAMPTZ | When detected |

## Files

- Ingest: `modal-mcp-server/src/ingest/signal_job_change_v2.py`
- Extraction: `modal-mcp-server/src/extraction/signal_job_change_v2.py`
- Migration: `supabase/migrations/20260130_signal_job_change.sql`
