# lookup_case_study_details

> **Last Updated:** 2026-02-04

## Purpose
Check whether a specific case study URL has already been extracted (exists in `extracted.case_study_details`).

## Endpoint
```
POST https://api.revenueinfra.com/run/companies/case-study-details/lookup
```

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-lookup-case-study-details.modal.run
```

## Request
```json
{
  "case_study_url": "https://www.andela.com/customer-stories/resy"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| case_study_url | string | Yes | The exact case study URL to check |

## Response
```json
{
  "exists": true,
  "case_study_url": "https://www.andela.com/customer-stories/resy"
}
```

## Table Checked
`extracted.case_study_details` — has a unique constraint on `case_study_url`.

## Use Case
Called from Clay before running Gemini extraction on a case study URL, to avoid re-extracting URLs that have already been processed.

## File
`/modal-functions/src/ingest/lookup_case_study_details.py`
