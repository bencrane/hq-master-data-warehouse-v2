# CRM Data Resolution Workflows

**Purpose:** Clean up messy CRM data by resolving missing fields using your existing database as a lookup source.

**Base URL:** `https://api.revenueinfra.com/api/workflows`

**Data Flow:**
```
hq.clients_raw_data → [normalize] → hq.clients_normalized_crm_data → [resolve-*] → filled gaps
```

---

## Overview

These endpoints take messy CRM records (missing domains, inconsistent names, no LinkedIn URLs, etc.) and attempt to fill in the gaps by matching against your existing data in `core.*`, `extracted.*`, and `reference.*` tables.

### Workflow Sequence (Recommended Order)

1. **`/normalize`** - Clean and standardize raw data first
2. **`/resolve-domain-from-email`** - Get domain from email addresses
3. **`/resolve-domain-from-linkedin`** - Get domain from company LinkedIn URLs
4. **`/resolve-company-name`** - Get cleaned company name from domain
5. **`/resolve-linkedin-from-domain`** - Get company LinkedIn from domain
6. **`/resolve-person-linkedin-from-email`** - Get person LinkedIn from email
7. **`/resolve-company-location-from-domain`** - Get company city/state/country
8. **`/resolve-person-location-from-linkedin`** - Get person city/state/country

---

## Tables Involved

### Input/Output Table
| Table | Purpose |
|-------|---------|
| `hq.clients_raw_data` | Raw CRM data uploaded by client |
| `hq.clients_normalized_crm_data` | Normalized + resolved data |

### Lookup Tables (Read-Only)
| Table | Used By | Fields Looked Up |
|-------|---------|------------------|
| `core.companies` | `/resolve-domain-from-linkedin`, `/resolve-linkedin-from-domain` | `domain`, `linkedin_url` |
| `core.company_locations` | `/resolve-company-location-from-domain` | `city`, `state`, `country` |
| `extracted.cleaned_company_names` | `/resolve-company-name` | `cleaned_company_name` |
| `extracted.person_discovery_location_parsed` | `/resolve-person-location-from-linkedin` | `city`, `state`, `country` |
| `reference.email_to_person` | `/resolve-domain-from-email`, `/resolve-person-linkedin-from-email` | `domain`, `person_linkedin_url` |

---

## Endpoint Details

---

### 1. POST `/api/workflows/normalize`

**Purpose:** Normalize raw CRM data - clean up formatting, standardize URLs, split names, etc.

**Input Table:** `hq.clients_raw_data`
**Output Table:** `hq.clients_normalized_crm_data`

#### Request

```json
// Option 1: By record IDs
{
  "record_ids": ["uuid1", "uuid2", "uuid3"]
}

// Option 2: By client domain (process all records for a client)
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_processed": 150,
  "errors": null
}
```

#### Normalization Rules Applied

| Field | Transformation |
|-------|----------------|
| `first_name`, `last_name` | Trim, title case |
| `full_name` | Built from first+last, or split from full_name if first/last missing |
| `domain` | Remove `https://`, `http://`, `www.`, paths, lowercase |
| `work_email` | Trim, lowercase |
| `person_linkedin_url` | Normalize to `https://www.linkedin.com/in/{slug}` |
| `company_linkedin_url` | Normalize to `https://www.linkedin.com/company/{slug}` |
| `*_city`, `*_state`, `*_country` | Trim, title case |
| `phone_number` | Trim only |
| `"null"` strings | Converted to actual `NULL` |

---

### 2. POST `/api/workflows/resolve-company-name`

**Purpose:** Get a clean, properly formatted company name from domain.

**Lookup Table:** `extracted.cleaned_company_names`
**Fallback:** Calls Parallel AI if no match found (and caches result)

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
// OR
{
  "record_ids": ["uuid1", "uuid2"]
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": 45,
  "records_already_had_value": 30,
  "records_matched": 40,
  "records_from_parallel": 5,
  "errors": null
}
```

#### Logic Flow

```
1. Record has domain?
   ├─ No → Skip
   └─ Yes → Check extracted.cleaned_company_names
             ├─ Found → Use it (source: "matched-extracted.cleaned_company_names")
             └─ Not found → Call Parallel AI
                            ├─ Success → Use it, write to extracted.cleaned_company_names (source: "parallel")
                            └─ Fail → Skip
```

#### Fields Updated
- `hq.clients_normalized_crm_data.cleaned_company_name`
- `hq.clients_normalized_crm_data.cleaned_company_name_source`

---

### 3. POST `/api/workflows/resolve-domain-from-linkedin`

**Purpose:** Get company domain from company LinkedIn URL.

**Lookup Table:** `core.companies` (matches on `linkedin_url`)

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": 25,
  "records_already_had_value": 50,
  "records_matched": 25,
  "records_no_match": 25,
  "errors": null
}
```

#### Logic Flow

```
1. Record has company_linkedin_url but missing domain?
   ├─ No → Skip
   └─ Yes → Lookup core.companies WHERE linkedin_url = {company_linkedin_url}
             ├─ Found → Set domain
             └─ Not found → Skip (no external API call)
```

#### Fields Updated
- `hq.clients_normalized_crm_data.domain`

---

### 4. POST `/api/workflows/resolve-domain-from-email`

**Purpose:** Get company domain from work email address.

**Lookup Table:** `reference.email_to_person` (first), then extract from email (fallback)

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": 80,
  "records_already_had_value": 10,
  "records_from_lookup": 20,
  "records_from_extraction": 60,
  "errors": null
}
```

#### Logic Flow

```
1. Record has work_email but missing domain?
   ├─ No → Skip
   └─ Yes → Lookup reference.email_to_person WHERE email = {work_email}
             ├─ Found → Use domain from lookup
             └─ Not found → Extract domain from email (part after @)
```

#### Fields Updated
- `hq.clients_normalized_crm_data.domain`

---

### 5. POST `/api/workflows/resolve-linkedin-from-domain`

**Purpose:** Get company LinkedIn URL from domain.

**Lookup Table:** `core.companies` (matches on `domain`)

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": 40,
  "records_already_had_value": 30,
  "records_matched": 40,
  "records_no_match": 30,
  "errors": null
}
```

#### Logic Flow

```
1. Record has domain but missing company_linkedin_url?
   ├─ No → Skip
   └─ Yes → Lookup core.companies WHERE domain = {domain}
             ├─ Found → Set company_linkedin_url
             └─ Not found → Skip
```

#### Fields Updated
- `hq.clients_normalized_crm_data.company_linkedin_url`

---

### 6. POST `/api/workflows/resolve-person-linkedin-from-email`

**Purpose:** Get person's LinkedIn URL from their work email.

**Lookup Table:** `reference.email_to_person`

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": 15,
  "records_already_had_value": 60,
  "records_matched": 15,
  "records_no_match": 25,
  "errors": null
}
```

#### Logic Flow

```
1. Record has work_email but missing person_linkedin_url?
   ├─ No → Skip
   └─ Yes → Lookup reference.email_to_person WHERE email = {work_email}
             ├─ Found → Set person_linkedin_url
             └─ Not found → Skip
```

#### Fields Updated
- `hq.clients_normalized_crm_data.person_linkedin_url`

---

### 7. POST `/api/workflows/resolve-company-location-from-domain`

**Purpose:** Get company city, state, country from domain.

**Lookup Table:** `core.company_locations`

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": {
    "city": 30,
    "state": 35,
    "country": 40
  },
  "records_all_fields_had_value": 20,
  "records_matched": 60,
  "records_no_match": 20,
  "errors": null
}
```

#### Logic Flow

```
1. Record has domain?
   ├─ No → Skip
   └─ Yes → Lookup core.company_locations WHERE domain = {domain}
             ├─ Found → Fill in missing city/state/country (COALESCE - won't overwrite existing)
             └─ Not found → Skip
```

#### Fields Updated (only if currently NULL)
- `hq.clients_normalized_crm_data.company_city`
- `hq.clients_normalized_crm_data.company_state`
- `hq.clients_normalized_crm_data.company_country`

---

### 8. POST `/api/workflows/resolve-person-location-from-linkedin`

**Purpose:** Get person's city, state, country from their LinkedIn URL.

**Lookup Table:** `extracted.person_discovery_location_parsed`

#### Request

```json
{
  "client_domain": "securitypalhq.com"
}
```

#### Response

```json
{
  "success": true,
  "records_evaluated": 100,
  "fields_updated": {
    "city": 20,
    "state": 25,
    "country": 30
  },
  "records_all_fields_had_value": 40,
  "records_matched": 35,
  "records_no_match": 25,
  "errors": null
}
```

#### Logic Flow

```
1. Record has person_linkedin_url?
   ├─ No → Skip
   └─ Yes → Lookup extracted.person_discovery_location_parsed WHERE linkedin_url = {person_linkedin_url}
             ├─ Found → Fill in missing city/state/country (COALESCE - won't overwrite existing)
             └─ Not found → Skip
```

#### Fields Updated (only if currently NULL)
- `hq.clients_normalized_crm_data.person_city`
- `hq.clients_normalized_crm_data.person_state`
- `hq.clients_normalized_crm_data.person_country`

---

## Full Pipeline Example

To process a client's messy CRM data through the full resolution pipeline:

```bash
# 1. Normalize raw data
curl -X POST https://api.revenueinfra.com/api/workflows/normalize \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 2. Resolve domains from emails
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-domain-from-email \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 3. Resolve domains from LinkedIn URLs
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-domain-from-linkedin \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 4. Resolve company names
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-company-name \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 5. Resolve company LinkedIn URLs
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-linkedin-from-domain \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 6. Resolve person LinkedIn URLs
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-person-linkedin-from-email \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 7. Resolve company locations
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-company-location-from-domain \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'

# 8. Resolve person locations
curl -X POST https://api.revenueinfra.com/api/workflows/resolve-person-location-from-linkedin \
  -H "Content-Type: application/json" \
  -d '{"client_domain": "securitypalhq.com"}'
```

---

## Response Field Glossary

| Field | Meaning |
|-------|---------|
| `records_evaluated` | Total records examined |
| `fields_updated` | Number of fields that were actually filled in |
| `records_already_had_value` | Records skipped because field already had data |
| `records_matched` | Records where a lookup match was found |
| `records_no_match` | Records where no lookup match was found |
| `records_from_parallel` | Records enriched via Parallel AI (only for `/resolve-company-name`) |
| `records_from_lookup` | Records enriched from lookup table |
| `records_from_extraction` | Records enriched from extraction (e.g., domain from email) |
| `errors` | Array of per-record errors, or `null` if none |

---

## Key Behaviors

1. **Non-destructive:** These endpoints never overwrite existing values. They only fill in `NULL` fields.

2. **Idempotent:** Running the same endpoint multiple times is safe - it will skip records that already have values.

3. **Batch-optimized:** All lookups are batched (e.g., lookup all unique domains at once, not one at a time).

4. **External API calls:** Only `/resolve-company-name` calls an external API (Parallel AI). All other endpoints are pure database lookups.

5. **Caching:** `/resolve-company-name` writes successful Parallel AI results back to `extracted.cleaned_company_names` for future lookups.

---

## Related Tables Schema

### hq.clients_raw_data
```sql
id                    UUID PRIMARY KEY
client_domain         TEXT        -- e.g., "securitypalhq.com"
first_name           TEXT
last_name            TEXT
full_name            TEXT
person_linkedin_url  TEXT
person_city          TEXT
person_state         TEXT
person_country       TEXT
work_email           TEXT
phone_number         TEXT
company_name         TEXT
domain               TEXT
company_linkedin_url TEXT
company_city         TEXT
company_state        TEXT
company_country      TEXT
raw_payload          JSONB       -- original data
```

### hq.clients_normalized_crm_data
```sql
id                            UUID PRIMARY KEY
raw_data_id                   UUID REFERENCES hq.clients_raw_data(id)
client_domain                 TEXT
-- All the same fields as raw, but normalized
first_name                    TEXT
last_name                     TEXT
full_name                     TEXT
person_linkedin_url           TEXT
-- ... etc ...
-- Plus resolved fields:
cleaned_company_name          TEXT
cleaned_company_name_source   TEXT  -- "matched-extracted.cleaned_company_names" or "parallel"
normalized_at                 TIMESTAMP
updated_at                    TIMESTAMP
```

---

*Last updated: 2026-02-16*
