# Modal Endpoints Reference

**Last Updated:** 2026-02-06
**App Name:** `hq-master-data-ingest`
**Dashboard:** https://modal.com/apps/bencrane/main/deployed/hq-master-data-ingest

---

## Table of Contents

1. [DB-Direct Endpoints (NEW)](#db-direct-endpoints-new)
2. [Company Ingest Endpoints](#company-ingest-endpoints)
3. [Person Ingest Endpoints](#person-ingest-endpoints)
4. [Signal Endpoints](#signal-endpoints)
5. [Lookup Endpoints](#lookup-endpoints)
6. [Location Lookup Ingest Endpoints](#location-lookup-ingest-endpoints)
7. [Backfill Endpoints](#backfill-endpoints)
8. [Other Endpoints](#other-endpoints)
9. [Utility Endpoints](#utility-endpoints)

---

## DB-Direct Endpoints (NEW)

These endpoints use direct PostgreSQL connections (psycopg2) instead of Supabase REST client.
They call external APIs AND write directly to the database.

**Secret Required:** `supabase-db-direct` with `DATABASE_URL` environment variable.

---

### classify_b2b_b2c_openai_db_direct

**URL:** `https://bencrane--hq-master-data-ingest-classify-b2b-b2c-openai-db-direct.modal.run`

**Purpose:** Classify company as B2B/B2C using OpenAI.

**Payload:**
```json
{
  "domain": "stripe.com",
  "company_name": "Stripe",
  "description": "Financial infrastructure for the internet",
  "model": "gpt-4o",
  "workflow_source": "openai-native/b2b-b2c/classify/db-direct"
}
```

**Stores to:**
- `raw.company_classification_db_direct`
- `extracted.company_classification_db_direct`
- `core.company_business_model`

---

### ingest_linkedin_ads_db_direct

**URL:** `https://bencrane--hq-master-data-ingest-ingest-linkedin-ads-db-direct.modal.run`

**Purpose:** Ingest LinkedIn ads data from Adyntel.

**Payload:**
```json
{
  "domain": "stripe.com",
  "linkedin_ads_payload": { "ads": [...] },
  "workflow_source": "adyntel-native/linkedin-ads/ingest/db-direct"
}
```

**Stores to:**
- `raw.linkedin_ads_payloads`
- `extracted.company_linkedin_ads`
- `core.company_linkedin_ads`

---

### ingest_meta_ads_db_direct

**URL:** `https://bencrane--hq-master-data-ingest-ingest-meta-ads-db-direct.modal.run`

**Purpose:** Ingest Meta (Facebook/Instagram) ads data from Adyntel.

**Payload:**
```json
{
  "domain": "stripe.com",
  "meta_ads_payload": { "ads": [...] },
  "workflow_source": "adyntel-native/meta-ads/ingest/db-direct"
}
```

**Stores to:**
- `raw.meta_ads_payloads`
- `extracted.company_meta_ads`
- `core.company_meta_ads`

---

### ingest_google_ads_db_direct

**URL:** `https://bencrane--hq-master-data-ingest-ingest-google-ads-db-direct.modal.run`

**Purpose:** Ingest Google ads data from Adyntel.

**Payload:**
```json
{
  "domain": "stripe.com",
  "google_ads_payload": { "creatives": [...] },
  "workflow_source": "adyntel-native/google-ads/ingest/db-direct"
}
```

**Stores to:**
- `raw.google_ads_payloads`
- `extracted.company_google_ads`
- `core.company_google_ads`

---

### infer_description_db_direct

**URL:** `https://bencrane--hq-master-data-ingest-infer-description-db-direct.modal.run`

**Purpose:** Infer company description using Parallel AI Task Enrichment API.

**Payload:**
```json
{
  "domain": "stripe.com",
  "company_name": "Stripe",
  "company_linkedin_url": "https://linkedin.com/company/stripe",
  "workflow_source": "parallel-native/description/infer/db-direct"
}
```

**Stores to:**
- `core.company_descriptions`

**Notes:** Uses async Parallel AI API (submit task → poll for completion).

---

## Company Ingest Endpoints

### ingest_clay_company_firmo

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-company-firmo.modal.run`

**Purpose:** Receive enriched company firmographic data.

**Payload:**
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-company-firmographics",
  "raw_payload": {}
}
```

**Stores to:** `raw.company_payloads` → `extracted.company_firmographics`

---

### ingest_clay_find_companies

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-find-companies.modal.run`

**Purpose:** Receive company discovery data from Clay Find Companies.

**Payload:**
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-find-companies",
  "raw_payload": {}
}
```

**Stores to:** `raw.company_discovery` → `extracted.company_discovery`

---

### ingest_clay_find_co_lctn_prsd

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-find-co-lctn-prsd.modal.run`

**Purpose:** Receive company discovery data with pre-parsed location.

**Payload:**
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-find-companies",
  "raw_company_payload": {},
  "raw_company_parsed_location_payload": {},
  "clay_table_url": "optional"
}
```

**Stores to:** `raw.company_discovery_location_parsed` → `extracted.company_discovery_location_parsed`

---

### ingest_all_comp_customers

**URL:** `https://bencrane--hq-master-data-ingest-ingest-all-comp-customers.modal.run`

**Purpose:** Bulk ingest company customers data.

---

### upsert_core_company

**URL:** `https://bencrane--hq-master-data-ingest-upsert-core-company.modal.run`

**Purpose:** Upsert core company record.

---

### ingest_manual_comp_customer

**URL:** `https://bencrane--hq-master-data-ingest-ingest-manual-comp-customer.modal.run`

**Purpose:** Manually ingest company customer relationship.

---

## Person Ingest Endpoints

### ingest_clay_person_profile

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-person-profile.modal.run`

**Purpose:** Receive enriched person profile data with full work history.

**Payload:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example",
  "workflow_slug": "clay-person-profile",
  "raw_payload": {}
}
```

**Stores to:** 
- `raw.person_payloads` 
- `extracted.person_profile`
- `extracted.person_experience`
- `extracted.person_education`

**Notes:** Upserts on `linkedin_url`. Only updates if `source_last_refresh` is newer.

---

### ingest_clay_find_people

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-find-people.modal.run`

**Purpose:** Receive person discovery data from Clay Find People.

**Payload:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example",
  "workflow_slug": "clay-find-people",
  "raw_payload": {},
  "cleaned_first_name": "optional",
  "cleaned_last_name": "optional",
  "cleaned_full_name": "optional",
  "clay_table_url": "optional"
}
```

**Stores to:** `raw.person_discovery` → `extracted.person_discovery`

**Notes:** Upserts on `linkedin_url`.

---

### ingest_clay_find_ppl_lctn_prsd

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-find-ppl-lctn-prsd.modal.run`

**Purpose:** Receive person discovery data with pre-parsed location.

**Payload:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example",
  "workflow_slug": "clay-find-people",
  "raw_person_payload": {},
  "raw_person_parsed_location_payload": {},
  "clay_table_url": "optional"
}
```

**Stores to:** `raw.person_discovery_location_parsed` → `extracted.person_discovery_location_parsed`

---

### ingest_ppl_title_enrich

**URL:** `https://bencrane--hq-master-data-ingest-ingest-ppl-title-enrich.modal.run`

**Purpose:** Receive person data with title enrichment (seniority, function, cleaned title).

**Payload:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example",
  "workflow_slug": "person-title-enrichment",
  "first_name": "optional",
  "last_name": "optional",
  "full_name": "optional",
  "cleaned_first_name": "optional",
  "cleaned_last_name": "optional",
  "cleaned_full_name": "optional",
  "location_name": "optional",
  "city": "optional",
  "state": "optional",
  "country": "optional",
  "has_city": false,
  "has_state": false,
  "has_country": false,
  "company_domain": "optional",
  "latest_title": "optional",
  "cleaned_job_title": "optional",
  "latest_company": "optional",
  "latest_start_date": "optional",
  "seniority_level": "optional",
  "job_function": "optional",
  "clay_table_url": "optional"
}
```

**Stores to:** `raw.person_title_enrichment` → `extracted.person_title_enrichment`

---

## Signal Endpoints

### ingest_clay_signal_new_hire

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-signal-new-hire.modal.run`

**Purpose:** Ingest new hire signal data.

**Payload:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/example",
  "workflow_slug": "clay-signal-new-hire",
  "raw_payload": {},
  "clay_table_url": "optional"
}
```

**Stores to:** `raw.signal_new_hire` → `extracted.signal_new_hire`

---

### ingest_clay_signal_job_posting

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-posting.modal.run`

**Purpose:** Ingest job posting signal data.

**Stores to:** `raw.signal_job_posting` → `extracted.signal_job_posting`

---

### ingest_clay_signal_job_change

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-change.modal.run`

**Purpose:** Ingest job change signal data.

**Stores to:** `raw.signal_job_change` → `extracted.signal_job_change`

---

### ingest_clay_signal_promotion

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-signal-promotion.modal.run`

**Purpose:** Ingest promotion signal data.

**Stores to:** `raw.signal_promotion` → `extracted.signal_promotion`

---

### ingest_clay_signal_news_fundraising

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-signal-news--9963a4.modal.run`

**Purpose:** Ingest news/fundraising signal data.

**Note:** URL truncated due to length.

**Stores to:** `raw.signal_news_fundraising` → `extracted.signal_news_fundraising`

---

## Lookup Endpoints

These query reference tables and return matches. They do NOT store data.

### lookup_person_location

**URL:** `https://bencrane--hq-master-data-ingest-lookup-person-location.modal.run`

**Purpose:** Check if a person location exists in lookup table.

**Table:** `reference.location_lookup`

**Payload:**
```json
{
  "location_name": "San Francisco, California, United States"
}
```

**Response (match found):**
```json
{
  "match_status": true,
  "location_name": "San Francisco, California, United States",
  "city": "San Francisco",
  "state": "California",
  "country": "United States",
  "has_city": true,
  "has_state": true,
  "has_country": true
}
```

**Response (no match):**
```json
{
  "match_status": false,
  "location_name": "...",
  "city": null,
  "state": null,
  "country": null,
  "has_city": null,
  "has_state": null,
  "has_country": null
}
```

---

### lookup_salesnav_location

**URL:** `https://bencrane--hq-master-data-ingest-lookup-salesnav-location.modal.run`

**Purpose:** Check if a SalesNav person location exists in lookup table.

**Table:** `reference.salesnav_location_lookup`

**Payload:**
```json
{
  "location_raw": "San Francisco, California, United States"
}
```

---

### lookup_salesnav_company_location

**URL:** `https://bencrane--hq-master-data-ingest-lookup-salesnav-company--1838bd.modal.run`

**Purpose:** Check if a SalesNav company location exists in lookup table.

**Table:** `reference.salesnav_company_location_lookup`

**Payload:**
```json
{
  "registered_address_raw": "San Francisco, California, United States"
}
```

---

### lookup_job_title

**URL:** `https://bencrane--hq-master-data-ingest-lookup-job-title.modal.run`

**Purpose:** Check if a job title exists in lookup table.

**Table:** `reference.job_title_lookup`

**Payload:**
```json
{
  "job_title": "VP of Marketing"
}
```

**Response (match found):**
```json
{
  "match_status": true,
  "job_title": "VP of Marketing",
  "cleaned_job_title": "VP Marketing",
  "seniority_level": "VP",
  "job_function": "Marketing"
}
```

---

## Location Lookup Ingest Endpoints

These INSERT data into location lookup tables.

### ingest_clay_company_location_lookup

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-company-loca-251127.modal.run`

**Purpose:** Add a company location to the Clay companies lookup table.

**Table:** `reference.clay_find_companies_location_lookup`

**Payload:**
```json
{
  "location_name": "Seattle, WA",
  "city": "Seattle",
  "state": "WA",
  "country": "United States",
  "has_city": true,
  "has_state": true,
  "has_country": false
}
```

**Notes:** Only `location_name` is required. Upserts on `location_name`.

---

### ingest_clay_person_location_lookup

**URL:** `https://bencrane--hq-master-data-ingest-ingest-clay-person-locat-6675ee.modal.run`

**Purpose:** Add a person location to the Clay people lookup table.

**Table:** `reference.clay_find_people_location_lookup`

**Payload:**
```json
{
  "location_name": "San Francisco, California, United States",
  "city": "San Francisco",
  "state": "California",
  "country": "United States",
  "has_city": true,
  "has_state": true,
  "has_country": true
}
```

**Notes:** Only `location_name` is required. Upserts on `location_name`.

---

## Backfill Endpoints

### backfill_person_location

**URL:** `https://bencrane--hq-master-data-ingest-backfill-person-location.modal.run`

**Purpose:** Batch update `extracted.person_discovery` with city/state/country from `reference.location_lookup`.

**Payload:**
```json
{
  "dry_run": true,
  "limit": null
}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dry_run` | `true` | If true, returns preview without updating |
| `limit` | `null` | Max records to update. null = all matching |

**Response (dry run):**
```json
{
  "dry_run": true,
  "records_missing_city": 520678,
  "lookup_entries": 9371,
  "matches_in_sample": 862,
  "sample_size": 1000,
  "sample_matches": [...],
  "message": "Set dry_run=False to execute update"
}
```

**Response (executed):**
```json
{
  "dry_run": false,
  "updated_count": 100,
  "processed_count": 136,
  "limit": 100,
  "errors": [],
  "error_count": 0
}
```

**Notes:** Only updates records where `city IS NULL`. Will not overwrite existing data.

---

## Other Endpoints

### ingest_vc_portfolio

**URL:** `https://bencrane--hq-master-data-ingest-ingest-vc-portfolio.modal.run`

**Purpose:** Ingest VC portfolio company data. Also attempts to match and update `crunchbase_domain_inference.linkedin_company_url`.

**Payload:**
```json
{
  "company_name": "Example Corp",
  "vc_name": "optional",
  "domain": "optional",
  "linkedin_url": "optional",
  "short_description": "optional",
  "long_description": "optional",
  "city": "optional",
  "state": "optional",
  "country": "optional",
  "employee_range": "optional",
  "founded_date": "optional",
  "operating_status": "optional",
  "workflow_slug": "vc-portfolio",
  "clay_table_url": "optional"
}
```

**Notes:** Only `company_name` is required. `workflow_slug` defaults to "vc-portfolio".

**Stores to:** `raw.vc_portfolio_payloads` → `extracted.vc_portfolio`

**Side effect:** If `domain` provided and matches `extracted.crunchbase_domain_inference.inferred_domain` where `linkedin_company_url IS NULL`, updates that record.

---

### ingest_case_study_extraction

**URL:** `https://bencrane--hq-master-data-ingest-ingest-case-study-extraction.modal.run`

**Purpose:** Ingest case study extraction data.

**Stores to:** `raw.case_study_payloads` → `extracted.case_study`

---

### ingest_icp_verdict

**URL:** `https://bencrane--hq-master-data-ingest-ingest-icp-verdict.modal.run`

**Purpose:** Ingest ICP verdict data.

**Stores to:** `raw.icp_verdict_payloads` → `extracted.icp_verdict`

---

### infer_crunchbase_domain

**URL:** `https://bencrane--hq-master-data-ingest-infer-crunchbase-domain.modal.run`

**Purpose:** Infer domain from Crunchbase data.

---

### ingest_company_address_parsing

**URL:** `https://bencrane--hq-master-data-ingest-ingest-company-address-parsing.modal.run`

**Purpose:** Ingest company address parsing data.

---

### command_center_email_enrichment

**URL:** `https://bencrane--hq-master-data-ingest-command-center-email-enrichment.modal.run`

**Purpose:** Email enrichment waterfall processing.

---

### get_email_job

**URL:** `https://bencrane--hq-master-data-ingest-get-email-job.modal.run`

**Purpose:** Get status of email enrichment job.

---

### generate_target_client_icp

**URL:** `https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run`

**Purpose:** Generate ICP criteria using OpenAI.

**Payload:**
```json
{
  "target_client_id": "uuid",
  "company_name": "Mutiny",
  "domain": "mutinyhq.com",
  "company_linkedin_url": "https://www.linkedin.com/company/mutinyhq"
}
```

**Stores to:** `raw.icp_payloads` → `extracted.target_client_icp`

---

## Utility Endpoints

### test_endpoint

**URL:** `https://bencrane--hq-master-data-ingest-test-endpoint.modal.run`

**Purpose:** Echo test for verifying deployment is working.

**Payload:**
```json
{
  "test": "hello"
}
```

**Response:**
```json
{
  "success": true,
  "received": {"test": "hello"}
}
```

---

## Disabled Endpoints

The following endpoints are in the codebase but currently disabled:

| Endpoint | File | Status |
|----------|------|--------|
| `ingest_salesnav_scrapes_person` | `ingest/salesnav_person.py` | Temporarily disabled |

---

## Workflow Registry

All workflows should be registered in `reference.enrichment_workflow_registry`:

| workflow_slug | provider | entity_type |
|---------------|----------|-------------|
| `clay-company-firmographics` | clay | company |
| `clay-find-companies` | clay | company |
| `clay-person-profile` | clay | person |
| `clay-find-people` | clay | person |
| `clay-signal-new-hire` | clay | signal |
| `clay-signal-job-posting` | clay | signal |
| `clay-signal-job-change` | clay | signal |
| `clay-signal-promotion` | clay | signal |
| `clay-signal-news-fundraising` | clay | signal |
| `person-title-enrichment` | clay | person |
| `vc-portfolio` | crunchbase | company |
| `ai-generate-target-client-icp` | openai | target_client |
