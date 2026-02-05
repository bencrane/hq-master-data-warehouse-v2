# send_case_study_urls_to_clay

> **Last Updated:** 2026-02-04

## Purpose
Sends staged case study URLs from `raw.staging_case_study_urls` to a Clay webhook for downstream Gemini extraction. Runs as a Modal function (not Railway) to avoid background task timeout issues.

## Endpoint
```
POST https://api.revenueinfra.com/run/case-study-urls/to-clay
```

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-send-case-study-urls-to-clay.modal.run
```

## Request
```json
{
  "webhook_url": "https://api.clay.com/v3/sources/webhook/...",
  "batch_id": "2026-02-04-companyenrich"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| webhook_url | string | Yes | Clay webhook URL to send records to |
| batch_id | string | No | Filter to a specific batch. If omitted, sends ALL unsent rows. |

## Response
```json
{
  "success": true,
  "total_rows": 1039,
  "sent": 1039
}
```

## How It Works
1. Queries `raw.staging_case_study_urls` for rows where `sent_to_clay = false`
2. Optionally filters by `batch_id`
3. For each row, POSTs to the webhook with payload: `origin_company_name`, `origin_company_domain`, `customer_company_name`, `case_study_url`
4. After each successful POST, marks that row `sent_to_clay = true`
5. Sleeps 100ms between sends (10 records/second — Clay rate limit)
6. Modal timeout: 600 seconds (10 minutes)

## Table: raw.staging_case_study_urls

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| origin_company_name | text | Company that published the case study |
| origin_company_domain | text | Publisher's domain |
| customer_company_name | text | Featured customer company |
| case_study_url | text | URL of the case study (unique constraint) |
| processed | boolean | Whether Gemini extraction results have been ingested back |
| sent_to_clay | boolean | Whether this row has been sent to the Clay webhook |
| batch_id | text | Optional batch identifier for filtering |
| created_at | timestamptz | Row creation time |

### Important: `sent_to_clay` vs `processed`
- `sent_to_clay = true` means the URL was fired to the Clay webhook
- `processed = true` means Gemini extraction is complete and results have been ingested back
- These are independent. A row can be sent but not yet processed.

## Upstream
Case study URLs are populated by `ingest_company_customers_structured` when customers have case study URLs.

## Downstream
Clay receives the URLs, runs Gemini extraction, and sends results back via:
- `ingest_case_study_extraction` → writes to `extracted.case_study_details` + `extracted.case_study_champions`
- `extract_case_study_buyer` → writes to `extracted.case_study_buyers`

## Lookup: Check If Already Extracted
```
POST https://api.revenueinfra.com/run/companies/case-study-details/lookup
```
```json
{ "case_study_url": "https://..." }
```
Returns `{ "exists": true/false }` from `extracted.case_study_details`.

## Known Issues (2026-02-04)

### origin_company_name was null for 1,040 rows
The first batch of 851 rows sent to Clay had `origin_company_name: null`. The staging table rows had null names because they were not populated during ingest (root cause not fully diagnosed — likely related to Supabase upsert behavior on conflict with pre-existing rows from older pipeline migration). Backfilled from `core.company_customers` and `core.companies` after the fact. 26 rows still have null names.

**Action needed:** Add validation to the send function — skip or warn when `origin_company_name` is null.

### Railway background task died (resolved)
Originally built as a Railway API endpoint using `asyncio.create_task()`. The background task died after the HTTP response completed, sending only 509/1039 rows. Moved to Modal function which runs synchronously with a 10-minute timeout.

## File
`/modal-functions/src/ingest/send_case_study_urls.py`
