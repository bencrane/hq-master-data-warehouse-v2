# Target Client Leads Endpoints

> **Last Updated:** 2026-02-03

## Purpose

Manage leads for target clients (demos/prospects). Separate from `client.*` schema which is for paying customers.

## Schema

The `target_client` schema mirrors `client` but is for demos:
- `target_client.leads` - denormalized lead records with FKs to core tables
- `target_client.leads_people` - normalized person data
- `target_client.leads_companies` - normalized company data

### Key Columns in target_client.leads

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| target_client_domain | TEXT | Identifies the prospect being demoed to |
| core_company_id | UUID | FK to core.companies (for enriched data) |
| core_person_id | UUID | FK to core.people (for enriched data) |
| first_name, last_name, full_name | TEXT | Person info |
| work_email | TEXT | Person email |
| company_domain, company_name | TEXT | Company info |
| source | TEXT | How lead was created (contact_form, csv_import, demo) |
| created_at | TIMESTAMPTZ | When created |

---

## Endpoints

### 1. Ingest Lead

Ingests a raw lead and looks up core FKs.

**URL:** `POST https://api.revenueinfra.com/run/target-client/leads/ingest`

**Request:**
```json
{
  "target_client_domain": "securitypalhq.com",
  "first_name": "AJ",
  "last_name": "Pahl",
  "work_email": "aj@harness.io",
  "company_domain": "harness.io",
  "source": "contact_form"
}
```

**Response:**
```json
{
  "success": true,
  "lead_id": "uuid",
  "person_id": "uuid",
  "company_id": "uuid",
  "core_company_id": "uuid-if-found",
  "core_person_id": "uuid-if-found"
}
```

---

### 2. List Leads

Returns leads with enriched data from core tables via joins.

**URL:** `POST https://api.revenueinfra.com/run/target-client/leads/list`

**Request:**
```json
{
  "target_client_domain": "securitypalhq.com",
  "source": "contact_form"
}
```

**Response:**
```json
{
  "success": true,
  "count": 1,
  "leads": [
    {
      "id": "uuid",
      "full_name": "AJ Pahl",
      "work_email": "aj@harness.io",
      "company_domain": "harness.io",
      "core_company_id": "uuid",
      "core_person_id": "uuid",
      "enriched_company": {
        "name": "Harness",
        "industry": "DevOps",
        "employee_count": 850,
        "city": "San Francisco"
      },
      "enriched_person": {
        "title": "VP Sales",
        "seniority": "VP",
        "department": "Sales"
      }
    }
  ]
}
```

---

### 3. Link Lead (Single)

Links existing core data to a target client lead. For demos where data is already enriched.

**URL:** `POST https://api.revenueinfra.com/run/target-client/leads/link`

**Request:**
```json
{
  "target_client_domain": "securitypalhq.com",
  "company_domain": "harness.io",
  "person_linkedin_url": "linkedin.com/in/ajpahl",
  "source": "demo"
}
```

**Response:**
```json
{
  "success": true,
  "lead_id": "uuid",
  "core_company_id": "uuid",
  "core_person_id": "uuid",
  "company_found": true,
  "person_found": true
}
```

---

### 4. Link Leads Batch (CSV Import)

Links multiple leads at once from a CSV import.

**URL:** `POST https://api.revenueinfra.com/run/target-client/leads/link-batch`

**Request:**
```json
{
  "target_client_domain": "securitypalhq.com",
  "source": "csv_import",
  "leads": [
    { "person_email": "aj@harness.io" },
    { "person_email": "jane@stripe.com" },
    { "person_email": "bob@datadog.com", "company_domain": "datadog.com" }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "total": 3,
  "linked": 2,
  "failed": 1,
  "results": [
    { "index": 0, "success": true, "lead_id": "...", "person_found": true, "company_found": true },
    { "index": 1, "success": true, "lead_id": "...", "person_found": true, "company_found": true },
    { "index": 2, "success": false, "error": "No matching person found in core.people" }
  ]
}
```

---

## File Locations

| File | Purpose |
|------|---------|
| `hq-api/routers/run.py` | All target-client endpoints |
| `supabase/migrations/20260203_target_client_schema.sql` | Schema creation |
| `supabase/migrations/20260203_target_client_leads_fks.sql` | FK columns |

## Architecture

```
target_client.leads
        │
        ├── core_company_id ──► core.companies (enriched company data)
        │
        └── core_person_id ──► core.people (enriched person data)
```

The list endpoint JOINs these tables to return fully enriched leads without additional API calls.
