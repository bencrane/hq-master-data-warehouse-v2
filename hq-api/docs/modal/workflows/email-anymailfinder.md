# Email: AnyMailFinder

Ingests email lookup results from AnyMailFinder. Stores raw payloads, extracts email data, and builds email-to-person reference mappings.

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-email-anymailfinder.modal.run
```

## Request Payload

```json
{
  "first_name": "",
  "last_name": "",
  "full_name": "",
  "person_linkedin_url": "",
  "company_name": "",
  "domain": "",
  "company_linkedin_url": "",
  "workflow_slug": "anymailfinder-email",
  "anymailfinder_raw_payload": {}
}
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `first_name` | string | No | Person's first name (from Clay context) |
| `last_name` | string | No | Person's last name (from Clay context) |
| `full_name` | string | No | Person's full name (from Clay context) |
| `person_linkedin_url` | string | No | Person's LinkedIn URL (from Clay context) |
| `company_name` | string | No | Company name (from Clay context) |
| `domain` | string | No | Company domain (from Clay context) |
| `company_linkedin_url` | string | No | Company LinkedIn URL (from Clay context) |
| `workflow_slug` | string | No | Defaults to `anymailfinder-email` |
| `anymailfinder_raw_payload` | object | **Yes** | Full AnyMailFinder response payload |

**Note:** Top-level fields (`first_name`, `last_name`, etc.) are your canonical values from Clay, NOT from the AnyMailFinder payload. This ensures data consistency.

## AnyMailFinder Payload Structure

```json
{
  "input": {
    "domain": "simplify.jobs",
    "full_name": "Michael Yan",
    "last_name": "Yan",
    "first_name": "Michael",
    "company_name": "Simplify",
    "not_found_error": false
  },
  "results": {
    "email": "michael@simplify.jobs",
    "validation": "valid",
    "alternatives": ["mike@simplify.jobs"]
  },
  "success": true
}
```

## Response

```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "email": "michael@simplify.jobs",
  "person_mapping_updated": true
}
```

## Extracted Fields

From the `anymailfinder_raw_payload`, we extract:

| Field | Source | Description |
|-------|--------|-------------|
| `email` | `results.email` | Found email address |
| `validation` | `results.validation` | `valid`, `unknown`, etc. |
| `alternatives` | `results.alternatives` | Array of alternative email formats |
| `success` | `success` | Whether lookup succeeded |
| `input_not_found_error` | `input.not_found_error` | AnyMailFinder error flag |

## Database Tables

### Raw Table: `raw.email_anymailfinder`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `person_linkedin_url` | TEXT | Person's LinkedIn URL |
| `first_name` | TEXT | First name |
| `last_name` | TEXT | Last name |
| `full_name` | TEXT | Full name |
| `domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `company_linkedin_url` | TEXT | Company LinkedIn URL |
| `workflow_slug` | TEXT | Workflow identifier |
| `clay_table_url` | TEXT | Source Clay table URL |
| `anymailfinder_raw_payload` | JSONB | Full AnyMailFinder response |
| `created_at` | TIMESTAMPTZ | When received |

### Extracted Table: `extracted.email_anymailfinder`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_payload_id` | UUID | Reference to raw table |
| `person_linkedin_url` | TEXT | Person's LinkedIn URL |
| `first_name` | TEXT | First name |
| `last_name` | TEXT | Last name |
| `full_name` | TEXT | Full name |
| `domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `company_linkedin_url` | TEXT | Company LinkedIn URL |
| `email` | TEXT | Found email address |
| `validation` | TEXT | Validation status |
| `alternatives` | TEXT[] | Alternative email formats |
| `success` | BOOLEAN | Lookup success flag |
| `input_not_found_error` | BOOLEAN | AnyMailFinder error flag |
| `created_at` | TIMESTAMPTZ | When extracted |

### Reference Table: `reference.email_to_person`

Built as a side effect of ingestion. Maps emails to LinkedIn profiles (first record wins, no overwrites).

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `email` | TEXT | Email address (unique) |
| `person_linkedin_url` | TEXT | Person's LinkedIn URL |
| `first_name` | TEXT | First name |
| `last_name` | TEXT | Last name |
| `full_name` | TEXT | Full name |
| `domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `source` | TEXT | Provider (e.g., `anymailfinder`) |
| `created_at` | TIMESTAMPTZ | When created |
| `updated_at` | TIMESTAMPTZ | When updated |

**Note:** This table uses INSERT with ON CONFLICT DO NOTHING. First record wins; subsequent records with the same email are skipped.

## Files

- Ingest: `modal-mcp-server/src/ingest/email_anymailfinder.py`
- Extraction: `modal-mcp-server/src/extraction/email_anymailfinder.py`
- Migration: `supabase/migrations/20260130_email_anymailfinder.sql`

## Validation Values

| Value | Meaning |
|-------|---------|
| `valid` | Email found and verified |
| `unknown` | Could not find email for this person |

## Usage Notes

1. **Canonical fields**: Always send your cleaned values in the top-level fields, not from AnyMailFinder's `input` object
2. **No overwrites**: Both extracted and reference tables use INSERT only
3. **Reference mapping**: Only created when both `email` and `person_linkedin_url` are present
4. **Empty emails**: Records with `validation: "unknown"` typically have empty email fields
