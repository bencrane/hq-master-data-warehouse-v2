# Modal Endpoints Reference

**App Name:** `hq-master-data-ingest`  
**Dashboard:** https://modal.com/apps/bencrane/main/deployed/hq-master-data-ingest

---

## Enriched Data Endpoints

These endpoints receive fully enriched data (detailed profiles with arrays).

### 1. Ingest Clay Company Firmo (Enriched)

**Endpoint:**  
```
https://bencrane--hq-master-data-ingest-ingest-clay-company-firmo.modal.run
```

**Method:** `POST`

**Workflow:** `clay-company-firmographics`

**Purpose:** Receives enriched company data and stores raw + extracted firmographics.

**Request Body:**
```json
{
  "company_domain": "openenvoy.com",
  "workflow_slug": "clay-company-firmographics",
  "raw_payload": {
    "url": "https://www.linkedin.com/company/openenvoy",
    "name": "OpenEnvoy",
    "slug": "openenvoy",
    "type": "Privately Held",
    "domain": "openenvoy.com",
    "org_id": 43237988,
    "country": "US",
    "founded": 2020,
    "website": "http://www.openenvoy.com",
    "industry": "Software Development",
    "locality": "San Mateo, California",
    "logo_url": "https://...",
    "locations": [...],
    "company_id": 111167945,
    "description": "OpenEnvoy is the Applied AI platform...",
    "specialties": ["SaaS", "Finance", "Fraud Prevention"],
    "last_refresh": "2024-10-19T23:31:39.952297",
    "employee_count": 69,
    "follower_count": 3983,
    "size": "51-200 employees"
  }
}
```

**Stores To:**
| Table | Purpose |
|-------|---------|
| `raw.company_payloads` | Raw JSONB payload |
| `extracted.company_firmographics` | Flattened fields (linkedin_url, name, industry, size, employee_count, country, etc.) |

**Response:**
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

### 2. Ingest Clay Person Profile (Enriched)

**Endpoint:**  
```
https://bencrane--hq-master-data-ingest-ingest-clay-person-profile.modal.run
```

**Method:** `POST`

**Workflow:** `clay-person-profile`

**Purpose:** Receives enriched person data including full work history and education. Extracts to profile, experience, and education tables.

**Request Body:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/andrewracine",
  "workflow_slug": "clay-person-profile",
  "raw_payload": {
    "url": "https://www.linkedin.com/in/andrewracine",
    "name": "Andrew Racine",
    "first_name": "Andrew",
    "last_name": "Racine",
    "slug": "andrewracine",
    "headline": "Marketing @ Writer",
    "title": "VP, Demand Generation & Growth",
    "summary": "I love helping companies grow.",
    "country": "United States",
    "location_name": "Santa Barbara, California, United States",
    "connections": 3211,
    "num_followers": 3501,
    "profile_id": 11321611,
    "jobs_count": 7,
    "picture_url_orig": "https://...",
    "last_refresh": "2024-10-22 23:52:44.766",
    
    "latest_experience": {
      "url": "https://www.linkedin.com/company/getwriter",
      "title": "VP, Demand Generation & Growth",
      "org_id": 67088679,
      "company": "Writer",
      "summary": "Writer is the full-stack generative AI platform...",
      "end_date": null,
      "locality": "San Francisco, California, United States",
      "is_current": true,
      "start_date": "2023-07-01",
      "company_domain": "writer.com"
    },
    
    "experience": [
      {
        "url": "https://www.linkedin.com/company/getwriter",
        "title": "VP, Demand Generation & Growth",
        "org_id": 67088679,
        "company": "Writer",
        "end_date": null,
        "locality": "San Francisco, California, United States",
        "is_current": true,
        "start_date": "2023-07-01",
        "company_domain": "writer.com"
      },
      {
        "url": "https://www.linkedin.com/company/fivetran",
        "title": "VP of Global Demand Generation",
        "org_id": 3954657,
        "company": "Fivetran",
        "end_date": "2023-07-01",
        "is_current": false,
        "start_date": "2019-12-01",
        "company_domain": "5tran.co"
      }
      // ... more experience entries
    ],
    
    "education": [
      {
        "degree": "Master of Business Administration (M.B.A.)",
        "school_name": "Babson F.W. Olin Graduate School of Business",
        "field_of_study": "Business Administration",
        "start_date": null,
        "end_date": null
      },
      {
        "degree": "Bachelor of Science",
        "school_name": "Providence College",
        "field_of_study": "Marketing"
      }
    ],
    
    "current_experience": [...],  // NOT used for extraction
    "certifications": null,
    "languages": null,
    "courses": null,
    "patents": null,
    "projects": null,
    "publications": null,
    "volunteering": null,
    "awards": null
  }
}
```

**Important Notes:**
- `latest_experience` (object) is flattened into person_profile — this is the current role snapshot
- `current_experience` (array) is NOT used — ignore it
- `experience` (array) is exploded into person_experience table
- `education` (array) is exploded into person_education table

**Stores To:**
| Table | Purpose |
|-------|---------|
| `raw.person_payloads` | Raw JSONB payload |
| `extracted.person_profile` | Core profile + latest_experience flattened |
| `extracted.person_experience` | 1 row per job from experience array |
| `extracted.person_education` | 1 row per school from education array |

**Upsert Logic:**
- Upserts on `linkedin_url`
- Only updates if incoming `source_last_refresh` > existing
- On upsert: deletes existing experience/education rows, re-inserts new ones

**Response:**
```json
{
  "success": true,
  "raw_id": "uuid",
  "person_profile_id": "uuid",
  "experience_count": 7,
  "education_count": 2
}
```

---

## Discovery Endpoints

These endpoints receive lightweight discovery data (no full arrays, just key fields).

### 3. Ingest Clay Find Companies (Discovery)

**Endpoint:**  
```
https://bencrane--hq-master-data-ingest-ingest-clay-find-companies.modal.run
```

**Method:** `POST`

**Workflow:** `clay-find-companies`

**Purpose:** Receives company discovery data from Clay "Find Companies" queries.

**Request Body:**
```json
{
  "company_domain": "example.com",
  "workflow_slug": "clay-find-companies",
  "raw_payload": {
    "domain": "example.com",
    "name": "Example Corp",
    "linkedin_url": "https://www.linkedin.com/company/example",
    "linkedin_company_id": 12345678,
    "clay_company_id": 87654321,
    "size": "51-200 employees",
    "type": "Privately Held",
    "country": "US",
    "location": "San Francisco, CA",
    "industry": "Software Development",
    "industries": ["Software Development", "SaaS"],
    "description": "Example Corp builds...",
    "annual_revenue": "25M-75M",
    "total_funding_amount_range_usd": "$100M - $250M",
    "resolved_domain": { ... },
    "derived_datapoints": { ... }
  }
}
```

**Stores To:**
| Table | Purpose |
|-------|---------|
| `raw.company_discovery` | Raw JSONB payload |
| `extracted.company_discovery` | Flattened fields + JSONB for industries, resolved_domain, derived_datapoints |

**Response:**
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

### 4. Ingest Clay Find People (Discovery)

**Endpoint:**  
```
https://bencrane--hq-master-data-ingest-ingest-clay-find-people.modal.run
```

**Method:** `POST`

**Workflow:** `clay-find-people`

**Purpose:** Receives person discovery data from Clay "Find People" queries. Lightweight — no full work history.

**Request Body:**
```json
{
  "linkedin_url": "https://www.linkedin.com/in/johndoe",
  "workflow_slug": "clay-find-people",
  "raw_payload": {
    "url": "https://www.linkedin.com/in/johndoe",
    "name": "John Doe",
    "first_name": "John",
    "last_name": "Doe",
    "location_name": "San Francisco, CA",
    "domain": "acme.com",
    "latest_experience_title": "VP Marketing",
    "latest_experience_company": "Acme Corp",
    "latest_experience_start_date": "2023-01-01",
    "company_table_id": "tbl_xxx",
    "company_record_id": "rec_xxx"
  }
}
```

**Stores To:**
| Table | Purpose |
|-------|---------|
| `raw.person_discovery` | Raw JSONB payload |
| `extracted.person_discovery` | Flattened fields including Clay reference IDs |

**Response:**
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
```

---

## ICP Generation Endpoint

### 5. Generate Target Client ICP

**Endpoint:**  
```
https://bencrane--hq-master-data-ingest-generate-target-client-icp.modal.run
```

**Method:** `POST`

**Workflow:** `ai-generate-target-client-icp`

**Purpose:** Takes target client info, calls OpenAI gpt-4o-mini to generate ICP criteria.

**Status:** ⚠️ Had issues during development — may need debugging

**Request Body:**
```json
{
  "target_client_id": "86f19e12-2d49-4878-a5ea-454d99369c09",
  "company_name": "Mutiny",
  "domain": "mutinyhq.com",
  "company_linkedin_url": "https://www.linkedin.com/company/mutinyhq"
}
```

**Expected Response:**
```json
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid",
  "icp": {
    "company_criteria": {
      "industries": ["Software Development"],
      "employee_count_min": 100,
      "employee_count_max": 5000,
      "countries": ["US", "United States"]
    },
    "person_criteria": {
      "title_contains_any": ["VP", "Director", "Head of"],
      "title_contains_all": ["Marketing", "Demand Gen", "Growth"]
    }
  }
}
```

**Stores To:**
| Table | Purpose |
|-------|---------|
| `raw.icp_payloads` | Raw OpenAI response |
| `extracted.target_client_icp` | Flattened ICP criteria |

---

## Workflow Registry

All workflows are registered in `reference.enrichment_workflow_registry`:

| workflow_slug | provider | platform | payload_type | entity_type |
|---------------|----------|----------|--------------|-------------|
| `clay-company-firmographics` | clay | clay | firmographics | company |
| `clay-person-profile` | clay | clay | profile | person |
| `clay-find-companies` | clay | clay | discovery | company |
| `clay-find-people` | clay | clay | discovery | person |
| `ai-generate-target-client-icp` | openai | modal | icp_criteria | target_client |

---

## Quick Reference

| Data Type | Endpoint | Workflow Slug |
|-----------|----------|---------------|
| **Company enriched** | ingest-clay-company-firmo | `clay-company-firmographics` |
| **Person enriched** | ingest-clay-person-profile | `clay-person-profile` |
| **Company discovery** | ingest-clay-find-companies | `clay-find-companies` |
| **Person discovery** | ingest-clay-find-people | `clay-find-people` |
| **ICP generation** | generate-target-client-icp | `ai-generate-target-client-icp` |

