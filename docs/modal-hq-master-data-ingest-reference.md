# HQ Master Data Ingest - Modal Function Reference

> **App Name:** `hq-master-data-ingest`  
> **App ID:** `ap-vzrCRdMftOzfP09pcATblG`  
> **Base URL:** `https://bencrane--hq-master-data-ingest-{function_name}.modal.run`  
> **Last Updated:** 2026-01-13

---

## Table of Contents

1. [ingest_clay_company_firmo](#1-ingest_clay_company_firmo)
2. [ingest_clay_find_companies](#2-ingest_clay_find_companies)
3. [ingest_all_comp_customers](#3-ingest_all_comp_customers)
4. [upsert_core_company](#4-upsert_core_company)
5. [ingest_manual_comp_customer](#5-ingest_manual_comp_customer)
6. [ingest_clay_person_profile](#6-ingest_clay_person_profile)
7. [ingest_clay_find_people](#7-ingest_clay_find_people)
8. [ingest_case_study_extraction](#8-ingest_case_study_extraction)
9. [command_center_email_enrichment](#9-command_center_email_enrichment)
10. [process_waterfall_batch](#10-process_waterfall_batch)
11. [get_email_job](#11-get_email_job)
12. [generate_target_client_icp](#12-generate_target_client_icp)

---

## 1. ingest_clay_company_firmo

### Purpose
Ingest enriched company payload from Clay's company firmographics workflow. Stores the raw payload, then extracts structured firmographic data.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-company-firmo.modal.run
```

### Expected Payload
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-company-firmographics",
  "raw_payload": {
    "name": "Example Corp",
    "url": "https://linkedin.com/company/example",
    "slug": "example-corp",
    "org_id": "12345",
    "company_id": "clay_abc123",
    "description": "A leading provider of...",
    "website": "https://example.com",
    "logo_url": "https://...",
    "type": "Public Company",
    "industry": "Software",
    "founded": 2010,
    "size": "51-200 employees",
    "employee_count": 150,
    "follower_count": 5000,
    "country": "United States",
    "locality": "San Francisco, CA",
    "locations": [
      {
        "is_primary": true,
        "city": "San Francisco",
        "country": "US"
      }
    ],
    "specialties": ["SaaS", "Enterprise Software"],
    "last_refresh": "2026-01-10T12:00:00Z"
  }
}
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `company_payloads` | INSERT |
| `extracted` | `company_firmographics` | UPSERT on `company_domain` |

### Calls
- `extract_company_firmographics()` — Extracts and flattens firmographic data

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

## 2. ingest_clay_find_companies

### Purpose
Ingest company discovery payload from Clay's find-companies workflow. Used for initial company discovery before full enrichment.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-find-companies.modal.run
```

### Expected Payload
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-find-companies",
  "raw_payload": {
    "name": "Example Corp",
    "linkedin_url": "https://linkedin.com/company/example",
    "linkedin_company_id": "12345",
    "clay_company_id": "clay_abc123",
    "size": "51-200",
    "type": "Private",
    "country": "United States",
    "location": "San Francisco, CA",
    "industry": "Software",
    "industries": ["Software", "Technology"],
    "description": "A leading provider...",
    "annual_revenue": "$10M-$50M",
    "total_funding_amount_range_usd": "$5M-$10M",
    "resolved_domain": "example.com",
    "derived_datapoints": {}
  }
}
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `company_discovery` | INSERT |
| `extracted` | `company_discovery` | UPSERT on `domain` |

### Calls
- `extract_find_companies()` — Extracts discovery data

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

## 3. ingest_all_comp_customers

### Purpose
Ingest customer research payload from Claygent's company customers workflow. Explodes an array of customers into individual rows.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-all-comp-customers.modal.run
```

### Expected Payload
```json
{
  "origin_company_domain": "vendor.com",
  "origin_company_name": "Vendor Corp",
  "origin_company_linkedin_url": "https://linkedin.com/company/vendor",
  "workflow_slug": "claygent-get-all-company-customers",
  "raw_payload": {
    "customers": [
      {
        "companyName": "Customer A",
        "url": "https://vendor.com/case-studies/customer-a",
        "hasCaseStudy": true
      },
      {
        "companyName": "Customer B",
        "url": null,
        "hasCaseStudy": false
      }
    ]
  }
}
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `company_customer_claygent_payloads` | INSERT |
| `extracted` | `company_customer_claygent` | UPSERT on `(origin_company_domain, company_customer_name)` — one row per customer |

### Calls
- `extract_company_customers_claygent()` — Explodes customers array into individual rows

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "customer_count": 2
}
```

---

## 4. upsert_core_company

### Purpose
Direct upsert to the `core.companies` table. Simple endpoint for adding/updating company records without going through the raw payload workflow.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-upsert-core-company.modal.run
```

### Expected Payload
```json
{
  "domain": "example.com",
  "name": "Example Corp",
  "linkedin_url": "https://linkedin.com/company/example"
}
```

| Field | Type | Required |
|-------|------|----------|
| `domain` | string | ✓ |
| `name` | string | |
| `linkedin_url` | string | |

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `core` | `companies` | UPSERT on `domain` |

### Calls
None

### Returns
```json
{
  "success": true,
  "id": "uuid",
  "domain": "example.com"
}
```

---

## 5. ingest_manual_comp_customer

### Purpose
Ingest manually-sourced company customer data. Data is already flattened (no extraction needed). Used for manually curated customer lists.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-manual-comp-customer.modal.run
```

### Expected Payload
```json
{
  "origin_company_domain": "vendor.com",
  "origin_company_name": "Vendor Corp",
  "origin_company_linkedin_url": "https://linkedin.com/company/vendor",
  "company_customer_name": "Big Customer Inc",
  "company_customer_domain": "bigcustomer.com",
  "company_customer_linkedin_url": "https://linkedin.com/company/bigcustomer",
  "case_study_url": "https://vendor.com/case-studies/big-customer",
  "has_case_study": true,
  "source_notes": "Found on website footer",
  "workflow_slug": "manual-company-customers"
}
```

| Field | Type | Required |
|-------|------|----------|
| `origin_company_domain` | string | ✓ |
| `origin_company_name` | string | |
| `origin_company_linkedin_url` | string | |
| `company_customer_name` | string | ✓ |
| `company_customer_domain` | string | |
| `company_customer_linkedin_url` | string | |
| `case_study_url` | string | |
| `has_case_study` | boolean | |
| `source_notes` | string | |
| `workflow_slug` | string | ✓ |

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `manual_company_customers` | UPSERT on `(origin_company_domain, company_customer_name)` |

### Calls
None — data is already flattened

### Returns
```json
{
  "success": true,
  "id": "uuid",
  "origin_company_domain": "vendor.com",
  "company_customer_name": "Big Customer Inc"
}
```

---

## 6. ingest_clay_person_profile

### Purpose
Ingest enriched person payload from Clay's person profile workflow. Extracts profile data, work experience array, and education array into separate tables.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-person-profile.modal.run
```

### Expected Payload
```json
{
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "workflow_slug": "clay-person-profile",
  "raw_payload": {
    "slug": "johndoe",
    "profile_id": "abc123",
    "first_name": "John",
    "last_name": "Doe",
    "name": "John Doe",
    "headline": "VP of Engineering at Example Corp",
    "summary": "Experienced engineering leader...",
    "country": "United States",
    "location_name": "San Francisco Bay Area",
    "connections": 500,
    "num_followers": 1200,
    "picture_url_orig": "https://...",
    "jobs_count": 5,
    "latest_experience": {
      "title": "VP of Engineering",
      "company": "Example Corp",
      "company_domain": "example.com",
      "url": "https://linkedin.com/company/example",
      "org_id": "12345",
      "locality": "San Francisco, CA",
      "start_date": "2022-03-01",
      "is_current": true
    },
    "experience": [
      {
        "title": "VP of Engineering",
        "company": "Example Corp",
        "company_domain": "example.com",
        "url": "https://linkedin.com/company/example",
        "org_id": "12345",
        "locality": "San Francisco, CA",
        "summary": "Leading engineering...",
        "start_date": "2022-03-01",
        "end_date": null,
        "is_current": true
      }
    ],
    "education": [
      {
        "school_name": "Stanford University",
        "degree": "BS",
        "field_of_study": "Computer Science",
        "grade": null,
        "activities": null,
        "start_date": "2005-09-01",
        "end_date": "2009-06-01"
      }
    ],
    "certifications": [],
    "languages": ["English", "Spanish"],
    "courses": [],
    "patents": [],
    "projects": [],
    "publications": [],
    "volunteering": [],
    "awards": [],
    "last_refresh": "2026-01-10T12:00:00Z"
  }
}
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `person_payloads` | INSERT |
| `extracted` | `person_profile` | UPSERT on `linkedin_url` (only if `source_last_refresh` is newer) |
| `extracted` | `person_experience` | DELETE existing + INSERT new (per `linkedin_url`) |
| `extracted` | `person_education` | DELETE existing + INSERT new (per `linkedin_url`) |

### Calls
- `extract_person_profile()` — Extracts profile with flattened `latest_experience`
- `extract_person_experience()` — Extracts experience array
- `extract_person_education()` — Extracts education array

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "person_profile_id": "uuid",
  "experience_count": 5,
  "education_count": 2
}
```

---

## 7. ingest_clay_find_people

### Purpose
Ingest person discovery payload from Clay's find-people workflow. Used for initial person discovery before full profile enrichment.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-find-people.modal.run
```

### Expected Payload
```json
{
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "workflow_slug": "clay-find-people",
  "raw_payload": {
    "first_name": "John",
    "last_name": "Doe",
    "name": "John Doe",
    "location_name": "San Francisco, CA",
    "domain": "example.com",
    "latest_experience_title": "VP of Engineering",
    "latest_experience_company": "Example Corp",
    "latest_experience_start_date": "2022-03-01",
    "company_table_id": "tbl_abc",
    "company_record_id": "rec_123"
  }
}
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `person_discovery` | INSERT |
| `extracted` | `person_discovery` | UPSERT on `linkedin_url` |

### Calls
- `extract_find_people()` — Extracts discovery data

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

## 8. ingest_case_study_extraction

### Purpose
Extract case study details using Gemini 2.0 Flash. Reads the case study URL, extracts article title, customer domain, and "champions" (quoted people).

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-ingest-case-study-extraction.modal.run
```

### Expected Payload
```json
{
  "origin_company_name": "Vendor Corp",
  "origin_company_domain": "vendor.com",
  "case_study_url": "https://vendor.com/case-studies/customer-a",
  "company_customer_name": "Customer A Inc",
  "has_case_study_url": true,
  "workflow_slug": "gemini-case-study-extraction"
}
```

| Field | Type | Required |
|-------|------|----------|
| `origin_company_name` | string | ✓ |
| `origin_company_domain` | string | ✓ |
| `case_study_url` | string | ✓ |
| `company_customer_name` | string | ✓ |
| `has_case_study_url` | boolean | ✓ |
| `workflow_slug` | string | ✓ |

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `case_study_extraction_payloads` | INSERT |
| `extracted` | `case_study_details` | UPSERT on `case_study_url` |
| `extracted` | `case_study_champions` | DELETE existing + INSERT new (per `case_study_id`) |

### Calls
- **Gemini 2.0 Flash API** — Extracts structured data from URL
- `extract_case_study_details()` — Stores extracted details
- `extract_case_study_champions()` — Stores champions (quoted people)

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "case_study_id": "uuid",
  "champion_count": 2,
  "customer_domain_found": true,
  "article_title": "How Customer A Increased Revenue 300% with Vendor Corp"
}
```

### Gemini Response Structure
```json
{
  "article_title": "Case Study Title",
  "customer_company_domain": "customer.com",
  "champions": [
    {
      "full_name": "Jane Smith",
      "job_title": "CTO",
      "company_name": "Customer A Inc"
    }
  ],
  "confidence": "high",
  "reasoning": "Found 1 champion quoted. Domain was hyperlinked."
}
```

---

## 9. command_center_email_enrichment

### Purpose
Fire-and-forget endpoint to send records to a Clay webhook at a rate-limited pace (8 requests/second). Returns immediately with a job ID for tracking.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-command-center-email-enrichment.modal.run
```

### Expected Payload
```json
{
  "records": [
    {
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "company": "Example Corp"
    },
    {
      "email": "jane@acme.com",
      "first_name": "Jane",
      "last_name": "Smith",
      "company": "Acme Inc"
    }
  ],
  "clay_webhook_url": "https://api.clay.com/v1/webhooks/abc123"
}
```

| Field | Type | Required |
|-------|------|----------|
| `records` | array of objects | ✓ |
| `clay_webhook_url` | string | ✓ |

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `email_waterfall_jobs` | INSERT (status: `pending`) |

### Calls
- `process_waterfall_batch.spawn()` — Spawns background worker

### Returns
```json
{
  "success": true,
  "job_id": "uuid",
  "total_records": 250
}
```

---

## 10. process_waterfall_batch

### Purpose
Background worker that sends records to Clay at 8/second rate limit. Updates job status as it progresses.

### Endpoint
```
None — Background function (not callable via HTTP)
```

### Parameters (Internal)
```python
job_id: str
records: List[dict]
clay_webhook_url: str
```

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `email_waterfall_jobs` | UPDATE status → `processing` |
| `raw` | `email_waterfall_jobs` | UPDATE status → `completed`, `sent_count`, `failed_count`, `completed_at` |

### Calls
- **httpx** — POSTs each record to `clay_webhook_url` with 125ms delay between requests

### Returns
None (async background task)

### Rate Limiting
- **8 records/second** (125ms sleep between requests)
- **10 minute timeout** (600 seconds)

---

## 11. get_email_job

### Purpose
Check the status of an email waterfall job created by `command_center_email_enrichment`.

### Endpoint
```
GET https://bencrane--hq-master-data-ingest-get-email-job.modal.run?job_id={job_id}
```

### Expected Payload
Query parameter: `job_id`

### Database Reads
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `email_waterfall_jobs` | SELECT by `id` |

### Calls
None

### Returns
```json
{
  "success": true,
  "job_id": "uuid",
  "status": "completed",
  "total_records": 250,
  "sent_count": 248,
  "failed_count": 2,
  "created_at": "2026-01-10T12:00:00Z",
  "completed_at": "2026-01-10T12:00:35Z"
}
```

### Job Statuses
| Status | Description |
|--------|-------------|
| `pending` | Job created, worker not yet started |
| `processing` | Worker is sending records |
| `completed` | All records processed |

---

## 12. generate_target_client_icp

### Purpose
Generate Ideal Customer Profile (ICP) criteria for a target client using OpenAI GPT-4o-mini. Used to define company and person filters for lead generation.

### Endpoint
```
POST https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run
```

### Expected Payload
```json
{
  "target_client_id": "uuid",
  "company_name": "Acme Corp",
  "domain": "acme.com",
  "company_linkedin_url": "https://linkedin.com/company/acme"
}
```

| Field | Type | Required |
|-------|------|----------|
| `target_client_id` | string | ✓ |
| `company_name` | string | ✓ |
| `domain` | string | ✓ |
| `company_linkedin_url` | string | |

### Database Writes
| Schema | Table | Operation |
|--------|-------|-----------|
| `raw` | `icp_payloads` | INSERT |
| `extracted` | `target_client_icp` | UPSERT on `target_client_id` |

### Calls
- **OpenAI GPT-4o-mini** — Generates ICP criteria

### Returns
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "icp": {
    "company_criteria": {
      "industries": ["Software", "Technology", "SaaS"],
      "employee_count_min": 50,
      "employee_count_max": 500,
      "size": ["51-200 employees", "201-500 employees"],
      "countries": ["United States", "Canada", "United Kingdom"],
      "founded_min": 2015,
      "founded_max": null
    },
    "person_criteria": {
      "title_contains_any": ["VP", "Director", "Head of", "Chief"],
      "title_contains_all": ["Engineering", "Technology", "Product"]
    }
  }
}
```

---

## Database Schema Reference

### Raw Tables (Landing Zone)

| Table | Purpose |
|-------|---------|
| `raw.company_payloads` | Raw company firmographic payloads |
| `raw.company_discovery` | Raw company discovery payloads |
| `raw.company_customer_claygent_payloads` | Raw Claygent customer research |
| `raw.manual_company_customers` | Manually curated customer data |
| `raw.person_payloads` | Raw person profile payloads |
| `raw.person_discovery` | Raw person discovery payloads |
| `raw.case_study_extraction_payloads` | Raw Gemini extraction responses |
| `raw.email_waterfall_jobs` | Email waterfall job tracking |
| `raw.icp_payloads` | Raw OpenAI ICP responses |

### Extracted Tables (Structured Data)

| Table | Purpose |
|-------|---------|
| `extracted.company_firmographics` | Structured company data |
| `extracted.company_discovery` | Structured discovery data |
| `extracted.company_customer_claygent` | Extracted customer relationships |
| `extracted.person_profile` | Structured person profiles |
| `extracted.person_experience` | Person work history (array) |
| `extracted.person_education` | Person education (array) |
| `extracted.person_discovery` | Structured person discovery |
| `extracted.case_study_details` | Extracted case study metadata |
| `extracted.case_study_champions` | People quoted in case studies |
| `extracted.target_client_icp` | Generated ICP criteria |

### Core Tables

| Table | Purpose |
|-------|---------|
| `core.companies` | Canonical company records |

---

## Workflow Registry

All ingest functions look up their `workflow_slug` in `reference.enrichment_workflow_registry` to get:
- `provider` — Data source (e.g., "clay", "gemini", "openai")
- `platform` — Platform used (e.g., "clay", "manual")
- `payload_type` — Type classification

---

## Error Handling

All functions return errors in this format:
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

Common errors:
- `"Workflow '{slug}' not found"` — Invalid workflow_slug
- `"Failed to parse Gemini response as JSON"` — Gemini returned invalid JSON
- Database constraint violations — Duplicate key, foreign key errors

---

## Secrets Required

| Secret Name | Used By |
|-------------|---------|
| `supabase-credentials` | All functions |
| `gemini-secret` | `ingest_case_study_extraction` |
| `openai-secret` | `generate_target_client_icp` |

---

## Deployment

```bash
cd modal-mcp-server/src
modal deploy app.py
```

**Rules:**
1. All code must be committed to main before deploy
2. Always deploy from `app.py` entry point
3. Always deploy from main branch
