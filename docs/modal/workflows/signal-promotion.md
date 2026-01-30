# Signal: Promotion

Detects when a person gets promoted (title change within same company).

## Endpoint

```
POST https://bencrane--hq-master-data-ingest-ingest-signal-promotion.modal.run
```

## Request Payload

```json
{
  "client_domain": "forethought.ai",
  "days_since_promotion": "90",
  "raw_promotion_payload": {...}
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `client_domain` | string | Client domain for multi-tenant tracking |
| `raw_promotion_payload` | object | Full payload from Clay |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `days_since_promotion` | integer/string | Days since promotion filter (Clay setting) |

## Response

```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "person_name": "Lynn Scavullo",
  "new_title": "VP Operations Support"
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

**Company (from `fullProfile.latest_experience`):**
- `company_domain`
- `company_name`
- `company_linkedin_url`

**Promotion Info:**
- `new_title` - New title after promotion
- `previous_title` - Title before promotion
- `new_role_start_date` - When new role started

**Confidence:**
- `confidence` - Score (0-100)
- `reduced_confidence_reasons` - Array of reasons if confidence reduced

## Database Tables

### Raw Table: `raw.signal_promotion_payloads`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `client_domain` | TEXT | Client domain |
| `origin_table_id` | TEXT | Clay table ID |
| `origin_record_id` | TEXT | Clay record ID |
| `raw_payload` | JSONB | Full payload |
| `created_at` | TIMESTAMPTZ | When received |

### Extracted Table: `extracted.signal_promotion`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_payload_id` | UUID | Reference to raw |
| `client_domain` | TEXT | Client domain |
| `person_name` | TEXT | Full name |
| `person_linkedin_url` | TEXT | LinkedIn URL |
| `company_domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `new_title` | TEXT | New title |
| `previous_title` | TEXT | Previous title |
| `new_role_start_date` | DATE | Role start date |
| `confidence` | INTEGER | Confidence score |
| `is_initial_check` | BOOLEAN | Initial check flag |
| `days_since_promotion` | INTEGER | Days filter (Clay setting) |
| `signal_detected_at` | TIMESTAMPTZ | When detected |

## Files

- Ingest: `modal-mcp-server/src/ingest/signal_promotion_v2.py`
- Extraction: `modal-mcp-server/src/extraction/signal_promotion_v2.py`
- Migration: `supabase/migrations/20260130_signal_promotion.sql`
