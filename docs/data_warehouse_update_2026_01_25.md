# Data Warehouse Update - January 25, 2026

## Overview

This document covers all data warehouse work completed on January 25, 2026, including new core tables for person tenure tracking, work history, promotions detection, data integration from Nostra ecom, VC portfolio cleanup, and new signal-based data ingestion tables.

---

## 1. Person Tenure & Work History Tables

### 1.1 core.person_tenure

Tracks job start dates for filtering by tenure (e.g., "started in last 6 months").

**Table:** `core.person_tenure`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `linkedin_url` | TEXT | Person LinkedIn URL (unique) |
| `job_start_date` | DATE | Start date of current job |
| `source` | TEXT | Data source (person_profile, person_discovery, salesnav) |
| `created_at` | TIMESTAMPTZ | Record creation time |

**Records:** 1,326,949

**Population Priority:**
1. `extracted.person_profile` (most reliable)
2. `extracted.person_discovery`
3. `extracted.salesnav_scrapes_person`

---

### 1.2 core.person_work_history

Full employment history for "worked at past customer" filtering.

**Table:** `core.person_work_history`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `linkedin_url` | TEXT | Person LinkedIn URL |
| `company_domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `company_linkedin_url` | TEXT | Company LinkedIn URL |
| `title` | TEXT | Job title |
| `matched_job_function` | TEXT | Standardized job function |
| `matched_seniority` | TEXT | Standardized seniority |
| `start_date` | DATE | Job start date |
| `end_date` | DATE | Job end date (NULL if current) |
| `is_current` | BOOLEAN | Whether this is current job |
| `experience_order` | INTEGER | Order in work history |
| `source_id` | UUID | Reference to source record |

**Records:** 1,239,481

**Index:** `(linkedin_url, company_domain)` for fast lookups

---

### 1.3 core.person_promotions

Detects and tracks promotions (same person, same company, different title, sequential dates).

**Table:** `core.person_promotions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `linkedin_url` | TEXT | Person LinkedIn URL |
| `company_domain` | TEXT | Company domain |
| `company_name` | TEXT | Company name |
| `previous_title` | TEXT | Title before promotion |
| `new_title` | TEXT | Title after promotion |
| `promotion_date` | DATE | Date of promotion |

**Records:** 284,383 promotions detected

**Promotion Detection Logic:**
- Same person (linkedin_url)
- Same company (company_domain)
- Different job title
- New job starts within 90 days of previous job ending

---

### 1.4 Auto-Sync Trigger

A trigger on `extracted.person_experience` automatically populates work history and detects promotions when new data flows in.

```sql
CREATE OR REPLACE FUNCTION sync_person_experience_to_core()
RETURNS TRIGGER AS $
BEGIN
  -- Insert into work history
  INSERT INTO core.person_work_history (...)
  VALUES (...);

  -- Check for promotion
  INSERT INTO core.person_promotions (...)
  SELECT ... WHERE promotion detected;

  RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_person_experience
AFTER INSERT ON extracted.person_experience
FOR EACH ROW
EXECUTE FUNCTION sync_person_experience_to_core();
```

---

## 2. Updated Views

### 2.1 core.people_full

Added `job_start_date` from `core.person_tenure`.

### 2.2 core.leads

Added `job_start_date` for API filtering.

**New Filtering Capabilities:**
```
GET /leads?job_start_date=gte.2024-01-01  -- Started in last year
GET /person_promotions?promotion_date=gte.2024-01-01  -- Recently promoted
GET /person_work_history?company_domain=eq.salesforce.com  -- Worked at Salesforce
```

---

## 3. Nostra Ecom Data Integration

Integrated 29,003 companies from `extracted.nostra_ecom_companies`.

### 3.1 Companies Added

| Table | Records Added |
|-------|---------------|
| `core.companies` | +23,956 |
| `core.company_descriptions` | +23,996 |
| `core.company_locations` | +24,554 |

### 3.2 Country Code Translation

Nostra data had country codes with trailing 'c' (e.g., "USc"). Fixed during import:

```sql
CASE RTRIM(country, 'c')
  WHEN 'US' THEN 'United States'
  WHEN 'GB' THEN 'United Kingdom'
  WHEN 'CA' THEN 'Canada'
  -- etc.
END
```

### 3.3 Updated Totals

| Table | Total Records |
|-------|---------------|
| `core.companies` | 525,526 |
| `core.company_descriptions` | 459,847 |
| `core.company_locations` | 399,992 |

---

## 4. VC Portfolio Cleanup

Normalized VC names in `extracted.vc_portfolio` to match canonical `raw.vc_firms` table.

### 4.1 Name Mappings Applied

| Portfolio Name | Canonical Name | Records Updated |
|----------------|----------------|-----------------|
| benchmark | Benchmark | 109 |
| Lightspeed Venture Partners | Lightspeed | 667 |
| New Enterprise Associates | NEA | 570 |
| NextView Ventures | NextView | 143 |
| Ribbit Capital | Ribbit | 127 |
| Sequoia Capital | Sequoia | 1,506 |
| Seven Seven Six Ventures | Seven Seven Six | 95 |
| Union Square Ventures | USV | 133 |

**Total Updated:** 3,350 records

### 4.2 New VC Added

Added to `raw.vc_firms`:
- Blue Owl (blueowl.com)

### 4.3 Verification

All 31 VC names in portfolio now have exact matches in canonical `raw.vc_firms` table.

---

## 5. New Table: instant_data_scraper

Created for Apollo data scraped via instant-data-scraper browser extension, with signal tracking.

### 5.1 Table Structure

**Table:** `raw.instant_data_scraper`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `payload` | JSONB | Raw payload |
| `created_at` | TIMESTAMPTZ | Record creation time |

**Table:** `extracted.instant_data_scraper`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `raw_payload_id` | UUID | Reference to raw record |
| `full_name` | TEXT | Full name |
| `first_name` | TEXT | First name |
| `last_name` | TEXT | Last name |
| `cleaned_full_name` | TEXT | Cleaned full name |
| `company_name` | TEXT | Company name |
| `cleaned_company_name` | TEXT | Cleaned company name |
| `person_linkedin_url` | TEXT | Person LinkedIn URL |
| `location` | TEXT | Location string |
| `job_title` | TEXT | Job title |
| `cleaned_job_title` | TEXT | Cleaned job title |
| `signal` | TEXT | Signal type (e.g., 'new-in-role') |
| `created_at` | TIMESTAMPTZ | Record creation time |

### 5.2 Signal Values

| Signal | Description |
|--------|-------------|
| `new-in-role` | Person recently started new role |

---

## 6. API Access Verification

All new tables and views are accessible via Supabase REST API:

| Endpoint | Schema | Status |
|----------|--------|--------|
| `/leads` | core | Working |
| `/person_work_history` | core | Working |
| `/person_promotions` | core | Working |
| `/person_tenure` | core | Working |

---

## 7. Deployment

- **GitHub:** Commit `907d1ed` pushed to main
- **Modal:** Deployed with new ingest endpoints including `ingest_instant_data_scraper`

---

## 8. Schema Summary (Updated)

### Core Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `core.companies` | Canonical company records | 525,526 |
| `core.people` | Canonical person records | 1,336,243 |
| `core.person_locations` | Person location data | 775,777 |
| `core.person_job_titles` | Job titles with mappings | 816,688 |
| `core.person_tenure` | Job start dates | 1,326,949 |
| `core.person_work_history` | Full employment history | 1,239,481 |
| `core.person_promotions` | Detected promotions | 284,383 |
| `core.company_industries` | Matched industries | 451,721 |
| `core.company_employee_range` | Employee ranges | 58,072 |
| `core.company_descriptions` | Descriptions & taglines | 459,847 |
| `core.company_locations` | Company locations | 399,992 |

### Core Views

| View | Purpose |
|------|---------|
| `core.companies_full` | Unified company view with all enrichments |
| `core.people_full` | Unified person view with all enrichments |
| `core.leads` | Combined people + companies for API filtering |

### Reference Tables

| Table | Purpose |
|-------|---------|
| `raw.vc_firms` | Canonical VC firm names (71 firms) |
| `reference.job_title_lookup` | Job title mappings |
| `reference.industry_lookup` | Industry mappings |
| `reference.employee_range_lookup` | Employee range mappings |
