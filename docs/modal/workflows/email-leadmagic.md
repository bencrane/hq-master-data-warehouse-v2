# Email: LeadMagic

Ingests email lookup results from LeadMagic. Stores raw payloads, extracts email data with employment verification, and builds email-to-person reference mappings.

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-email-leadmagic.modal.run
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
  "workflow_slug": "leadmagic-email",
  "leadmagic_raw_payload": {}
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
| `workflow_slug` | string | No | Defaults to `leadmagic-email` |
| `leadmagic_raw_payload` | object | **Yes** | Full LeadMagic response payload |

## LeadMagic Payload Structure

```json
{
  "email": "nick_mehta@gainsight.com",
  "domain": "gainsight.com",
  "has_mx": true,
  "status": "valid_catch_all",
  "message": "Email found",
  "last_name": "Mehta",
  "mx_record": "us-smtp-inbound-1.mimecast.com",
  "first_name": "Nick",
  "mx_provider": "Mimecast",
  "mx_records_full": [
    {"exchange": "us-smtp-inbound-1.mimecast.com", "priority": 0},
    {"exchange": "us-smtp-inbound-2.mimecast.com", "priority": 0}
  ],
  "credits_consumed": 1,
  "employment_verified": true,
  "is_domain_catch_all": true,
  "mx_security_gateway": true
}
```

## Response

```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "email": "nick_mehta@gainsight.com",
  "person_mapping_updated": true
}
```

## Extracted Fields

| Field | Type | Description |
|-------|------|-------------|
| `email` | TEXT | Found email address |
| `status` | TEXT | `valid_catch_all`, `valid`, `invalid`, etc. |
| `message` | TEXT | "Email found", etc. |
| `has_mx` | BOOLEAN | MX record exists |
| `mx_record` | TEXT | Primary MX record |
| `mx_provider` | TEXT | "Mimecast", "Google", etc. |
| `is_domain_catch_all` | BOOLEAN | Domain accepts all emails |
| `employment_verified` | BOOLEAN | Person still works there |
| `mx_security_gateway` | BOOLEAN | Has security gateway |
| `credits_consumed` | INTEGER | API credits used |

## Database Tables

### Raw Table: `raw.email_leadmagic`

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
| `leadmagic_raw_payload` | JSONB | Full LeadMagic response |
| `created_at` | TIMESTAMPTZ | When received |

### Extracted Table: `extracted.email_leadmagic`

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
| `status` | TEXT | Validation status |
| `message` | TEXT | Status message |
| `has_mx` | BOOLEAN | MX record exists |
| `mx_record` | TEXT | Primary MX record |
| `mx_provider` | TEXT | MX provider name |
| `is_domain_catch_all` | BOOLEAN | Catch-all domain |
| `employment_verified` | BOOLEAN | Person still works there |
| `mx_security_gateway` | BOOLEAN | Has security gateway |
| `credits_consumed` | INTEGER | API credits used |
| `created_at` | TIMESTAMPTZ | When extracted |

### Reference Table: `reference.email_to_person`

Shared with other email providers. Maps emails to LinkedIn profiles (first record wins, no overwrites).

| Column | Type | Description |
|--------|------|-------------|
| `email` | TEXT | Email address (unique) |
| `person_linkedin_url` | TEXT | Person's LinkedIn URL |
| `source` | TEXT | Provider (`leadmagic`, `anymailfinder`, etc.) |

## Files

- Ingest: `modal-mcp-server/src/ingest/email_leadmagic.py`
- Extraction: `modal-mcp-server/src/extraction/email_leadmagic.py`
- Migration: `supabase/migrations/20260130_email_leadmagic.sql`

## Status Values

| Value | Meaning |
|-------|---------|
| `valid` | Email verified and deliverable |
| `valid_catch_all` | Email found, domain accepts all |
| `invalid` | Email not deliverable |
| `unknown` | Could not verify |

## Key Differences from AnyMailFinder

- Includes `employment_verified` - indicates if person still works at company
- Includes MX record details (`has_mx`, `mx_record`, `mx_provider`, `mx_security_gateway`)
- Includes `is_domain_catch_all` flag
- Different email format detection (may find different emails than AnyMailFinder)
