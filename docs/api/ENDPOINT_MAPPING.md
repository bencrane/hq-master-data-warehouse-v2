# Endpoint Mapping

Maps Modal serverless functions to their API wrapper endpoints at `api.revenueinfra.com`.

**Last Updated:** 2026-02-16
**Total API Endpoints:** 312
**Total Modal Functions:** 109
**`/run/*` Endpoints:** 120

---

## Quick Stats

| Router | Endpoint Count | Description |
|--------|---------------|-------------|
| `run.py` | 120 | Modal function wrappers |
| `admin.py` | 70 | Admin/backoffice operations |
| `companies.py` | 45 | Company data queries |
| `leads.py` | 12 | Lead management |
| `filters.py` | 10 | Filter/search operations |
| `workflows.py` | 8 | Data resolution workflows |
| `hq.py` | 8 | HQ-specific operations |
| `enrichment.py` | 7 | Enrichment workflows |
| `parallel_native.py` | 7 | Parallel AI integrations |
| `auth.py` | 6 | Authentication |
| `pipeline.py` | 6 | Data pipeline operations |
| `job_boards.py` | 4 | Job board data |
| `people.py` | 4 | People data queries |
| `read.py` | 3 | Generic read operations |
| `views.py` | 2 | Target client views |

---

## Convention

| Component | Pattern |
|-----------|---------|
| Modal function | `ingest_clay_find_companies` |
| Modal URL | `https://bencrane--hq-master-data-ingest-{function-name}.modal.run` |
| API endpoint | `POST /run/{entity}/{platform}/{workflow}/{action}` |

---

## /run/* Endpoints (Modal Wrappers)

### Companies - Clay Native

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/clay-native/firmographics/ingest` | `ingest-clay-company-firmo` | Ingest company firmographics from Clay |
| `POST /run/companies/clay-native/find-companies/ingest` | `ingest-clay-find-companies` | Ingest discovered companies from Clay |
| `POST /run/companies/clay-native/normalize-company/ingest` | `ingest-cleaned-company-name` | Normalize/clean company names |
| `POST /run/companies/clay-native/signal-job-posting-2/ingest` | `ingest-clay-signal-job-posting` | Ingest job posting signals |

### Companies - Gemini Inference

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/gemini/type-classification/ingest` | `ingest-company-classification` | Classify company type (B2B/B2C) |
| `POST /run/companies/gemini/annual-commitment/infer` | `infer-annual-commitment` | Infer annual commitment requirement |
| `POST /run/companies/gemini/billing-default/infer` | `infer-billing-default` | Infer default billing cycle |
| `POST /run/companies/gemini/country/infer` | `infer-company-country` | Infer company country |
| `POST /run/companies/gemini/employee-range/infer` | `infer-company-employee-range` | Infer employee count range |
| `POST /run/companies/gemini/industry/infer` | `infer-company-industry` | Infer company industry |
| `POST /run/companies/gemini/linkedin-url/get` | `infer-company-linkedin-url` | Get company LinkedIn URL |
| `POST /run/companies/gemini/comparison-page-check/infer` | `infer-comparison-page-exists` | Check if comparison page exists |
| `POST /run/companies/gemini/crunchbase-url/get` | `infer-crunchbase-domain` | Get Crunchbase URL |
| `POST /run/companies/gemini/enterprise-tier-check/infer` | `infer-enterprise-tier-exists` | Check enterprise tier availability |
| `POST /run/companies/gemini/free-trial-check/infer` | `infer-free-trial` | Check free trial availability |
| `POST /run/companies/gemini/min-seats-check/infer` | `infer-minimum-seats` | Check minimum seat requirements |
| `POST /run/companies/gemini/money-back-check/infer` | `infer-money-back-guarantee` | Check money-back guarantee |
| `POST /run/companies/gemini/tier-number-check/infer` | `infer-number-of-tiers` | Count pricing tiers |
| `POST /run/companies/gemini/plan-naming-check/infer` | `infer-plan-naming-style` | Analyze plan naming convention |
| `POST /run/companies/gemini/pricing-model-check/infer` | `infer-pricing-model` | Infer pricing model type |
| `POST /run/companies/gemini/pricing-visibility-check/infer` | `infer-pricing-visibility` | Check pricing page visibility |
| `POST /run/companies/gemini/sales-motion-check/infer` | `infer-sales-motion` | Infer sales motion type |
| `POST /run/companies/gemini/security-gating-check/infer` | `infer-security-gating` | Check security/compliance gating |
| `POST /run/companies/gemini/webinars-status-data/infer` | `infer-webinars` | Check webinar availability |
| `POST /run/companies/gemini/add-ons-offered/infer` | `infer-add-ons-offered` | Check add-ons availability |
| `POST /run/companies/gemini/icp-fit-criterion/ingest` | `ingest-icp-fit-criterion` | Ingest ICP fit criteria |
| `POST /run/companies/gemini/icp-industries/ingest` | `ingest-icp-industries` | Ingest ICP industries |
| `POST /run/companies/gemini/icp-job-titles/ingest` | `ingest-icp-job-titles` | Ingest ICP job titles |
| `POST /run/companies/gemini/icp-value-prop/ingest` | `ingest-icp-value-proposition` | Ingest ICP value proposition |
| `POST /run/companies/gemini/icp-verdict/ingest` | `ingest-icp-verdict` | Ingest ICP verdict |
| `POST /run/companies/gemini/icp-job-posting/ingest` | `ingest-job-posting` | Ingest job posting data |
| `POST /run/companies/gemini/case-study-extraction/ingest` | `ingest-case-study-extraction` | Extract case study details |
| `POST /run/companies/gemini/resolve-customer-domain/ingest` | `resolve-customer-domain` | Resolve customer domains |

### Companies - Parallel AI (DB Direct)

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/parallel-native/description/infer/db-direct` | `infer-description-db-direct` | Infer company description |
| `POST /run/companies/parallel-native/description/infer/db-direct/batch` | `infer-description-db-direct` | Batch description inference |
| `POST /run/companies/parallel-native/employees/infer/db-direct` | `infer-employees-db-direct` | Infer employee count |
| `POST /run/companies/parallel-native/funding/infer/db-direct` | `infer-funding-db-direct` | Infer funding status |
| `POST /run/companies/parallel-native/g2-url/infer/db-direct` | `infer-g2-url-db-direct` | Infer G2 page URL |
| `POST /run/companies/parallel-native/g2-url/infer/db-direct/batch` | `infer-g2-url-db-direct` | Batch G2 URL inference |
| `POST /run/companies/parallel-native/last-funding-date/infer/db-direct` | `infer-last-funding-date-db-direct` | Infer last funding date |
| `POST /run/companies/parallel-native/revenue/infer/db-direct` | `infer-revenue-db-direct` | Infer company revenue |
| `POST /run/companies/parallel-task/competitors/infer/db-direct` | `discover-competitors-openai` | Discover competitors |
| `POST /run/companies/parallel-task/hq-location/infer/db-direct` | - | Infer HQ location |
| `POST /run/companies/parallel-task/industry/infer/db-direct` | - | Infer industry |
| `POST /run/companies/openai-native/b2b-b2c/classify/db-direct` | `classify-b2b-b2c-openai-db-direct` | Classify B2B/B2C |
| `POST /run/companies/gemini-native/g2-insights/extract/db-direct` | `extract-g2-insights-db-direct` | Extract G2 insights |

### Companies - Ads Data

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/clay-adyntel/linkedin-ads/ingest` | `ingest-linkedin-ads` | Ingest LinkedIn ads data |
| `POST /run/companies/clay-adyntel/meta-ads/ingest` | `ingest-meta-ads` | Ingest Meta/Facebook ads data |
| `POST /run/companies/clay-adyntel/google-ads/ingest` | `ingest-google-ads` | Ingest Google ads data |
| `POST /run/companies/adyntel-native/linkedin-ads/ingest/db-direct` | `ingest-linkedin-ads-db-direct` | LinkedIn ads (DB direct) |
| `POST /run/companies/adyntel-native/meta-ads/ingest/db-direct` | `ingest-meta-ads-db-direct` | Meta ads (DB direct) |
| `POST /run/companies/adyntel-native/google-ads/ingest/db-direct` | `ingest-google-ads-db-direct` | Google ads (DB direct) |

### Companies - Tech Stack

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/clay-predictleads/get-tech-stack/ingest` | `ingest-predictleads-techstack` | Ingest PredictLeads tech stack |
| `POST /run/companies/built-with/site-tech/ingest` | `ingest-builtwith` | Ingest BuiltWith tech data |

### Companies - Third Party Enrichment

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/clay-leadmagic/enrich/ingest` | `ingest-leadmagic-company` | LeadMagic company enrichment |
| `POST /run/companies/companyenrich/ingest` | `ingest-companyenrich` | CompanyEnrich data |
| `POST /run/companies/companyenrich/similar-companies-preview-results/ingest` | `ingest-companyenrich-sim-*` | Similar companies preview |
| `POST /run/companies/salesnav/scraped-data/ingest` | `ingest-salesnav-company` | SalesNav company data |

### Companies - Claygent (AI Agent)

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/claygent/customers-of-1/ingest` | `ingest-all-comp-customers` | Get all company customers v1 |
| `POST /run/companies/claygent/customers-of-2/ingest` | `ingest-company-customers-v2` | Get company customers v2 |
| `POST /run/companies/claygent/customers-of-3/ingest` | `ingest-company-customers-85468a` | Get company customers (structured) |
| `POST /run/companies/claygent/customers-of-4/ingest` | `ingest-company-customers-a12938` | Get company customers (claygent) |
| `POST /run/companies/claygent/company-address-parsing/ingest` | `ingest-company-address-parsing` | Parse company addresses |

### Companies - Database Operations

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/db/company-customers/lookup` | `lookup-company-customers` | Lookup company customers |
| `POST /run/companies/db/company-business-model/lookup` | `lookup-company-business-model` | Lookup business model |
| `POST /run/companies/db/company-description/lookup` | `lookup-company-description` | Lookup company description |
| `POST /run/companies/db/company-icp/lookup` | `lookup-company-icp` | Lookup company ICP |
| `POST /run/companies/db/similar-companies/lookup` | `lookup-similar-companies` | Lookup similar companies |
| `POST /run/companies/db/salesnav-company-location/lookup` | `lookup-salesnav-company-*` | Lookup SalesNav company location |
| `POST /run/companies/db/has-raised-vc-status/check` | `has-raised-vc` | Check VC funding status |
| `POST /run/companies/db/company-linkedin/update` | `update-staging-company-linkedin` | Update LinkedIn URL |
| `POST /run/companies/db/vc-domain/update` | `update-vc-domain` | Update VC domain |
| `POST /run/companies/db/core-company/upsert` | `upsert-core-company` | Upsert core company |
| `POST /run/companies/db/core-company-full/upsert` | `upsert-core-company-full` | Upsert full core company |
| `POST /run/companies/db/icp-criteria/upsert` | `upsert-icp-criteria` | Upsert ICP criteria |
| `POST /run/companies/db/populate-name/backfill` | `backfill-cleaned-company-name` | Backfill company names |
| `POST /run/companies/db/populate-description/backfill` | `backfill-company-descriptions` | Backfill descriptions |
| `POST /run/companies/db/public-ticker/backfill` | - | Backfill public tickers |

### Companies - Manual/Other

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/manual/customers/ingest` | `ingest-manual-comp-customer` | Manual customer input |
| `POST /run/companies/manual/public-company-check/ingest` | `ingest-public-company` | Check public company status |
| `POST /run/companies/manual/core-data/ingest` | `ingest-core-company-simple` | Ingest core company data |
| `POST /run/companies/not-sure/case-study-buyers/ingest` | `ingest-case-study-buyers` | Ingest case study buyers |
| `POST /run/companies/cb/vc-portfolio/ingest` | `ingest-cb-vc-portfolio` | Ingest Crunchbase VC portfolio |
| `POST /run/companies/cb/company-investors/ingest` | `ingest-company-vc-investors` | Ingest company investors |
| `POST /run/companies/ticker/ingest` | `ingest-company-ticker` | Ingest company ticker |

### Companies - SEC Filings

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/sec/filings/fetch` | `fetch-sec-filings` | Fetch SEC filings |
| `POST /run/companies/sec/financials/fetch` | `ingest-sec-financials` | Fetch SEC financials |

### Companies - Case Studies

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/companies/case-study-details/lookup` | `lookup-case-study-details` | Lookup case study details |
| `POST /run/case-study-urls/to-clay` | `send-case-study-urls-to-clay` | Send case study URLs to Clay |

### People - Clay Native

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/people/clay-native/find-people/ingest` | `ingest-clay-find-people` | Ingest discovered people |
| `POST /run/people/clay-native/person-profile/ingest` | `ingest-clay-person-profile` | Ingest person profiles |
| `POST /run/people/clay-native/signal-job-change/ingest` | `ingest-signal-job-change` | Job change signals v1 |
| `POST /run/people/clay-native/signal-job-change-2/ingest` | `ingest-clay-signal-job-change` | Job change signals v2 |
| `POST /run/people/clay-native/signal-job-posting/ingest` | `ingest-signal-job-posting` | Job posting signals |
| `POST /run/people/clay-native/signal-promotion/ingest` | `ingest-signal-promotion` | Promotion signals v1 |
| `POST /run/people/clay-native/signal-promotion-2/ingest` | `ingest-clay-signal-promotion` | Promotion signals v2 |
| `POST /run/people/clay-native/signal-new-hire-2/ingest` | `ingest-clay-signal-new-hire` | New hire signals |

### People - Email Enrichment

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/people/clay-anymail/get-email/ingest` | `ingest-email-anymailfinder` | AnyMailFinder email lookup |
| `POST /run/people/clay-icypeas/get-email/ingest` | `ingest-email-icypeas` | Icypeas email lookup |
| `POST /run/people/clay-leadmagic/get-email/ingest` | `ingest-email-leadmagic` | LeadMagic email lookup |

### People - Database Operations

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/people/db/person-job-title/lookup` | `lookup-job-title` | Lookup person job title |
| `POST /run/people/db/person-location/lookup` | `lookup-person-location` | Lookup person location |
| `POST /run/people/db/populate-location/backfill` | `backfill-person-location` | Backfill person locations |
| `POST /run/people/db/populate-matched-location/backfill` | `backfill-person-matched-*` | Backfill matched locations |
| `POST /run/--/db/salesnav-person/lookup` | `lookup-salesnav-location` | Lookup SalesNav person |

### People - Other

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/people/salesnav/scraped-data/ingest` | `ingest-salesnav-person` | Ingest SalesNav person data |
| `POST /run/people/not-sure/job-title-clean/ingest` | `ingest-ppl-title-enrich` | Clean/enrich job titles |

### Reference Data

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/reference/job-title/update` | - | Update job title reference |
| `POST /run/reference/location/update` | - | Update location reference |

### Target Client / Leads

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/target-client/leads/ingest` | - | Ingest target client lead |
| `POST /run/target-client/leads/list` | `lookup-client-leads` | List target client leads |
| `POST /run/target-client/leads/link` | - | Link lead to target client |
| `POST /run/target-client/leads/link-batch` | - | Batch link leads |
| `POST /run/client/leads/ingest` | - | Ingest client lead |
| `POST /run/client/leads/to-clay` | `send-client-leads-to-clay` | Send leads to Clay |

### Clay Export / Integration

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/salesnav/export/to-clay` | - | Export SalesNav data to Clay |
| `POST /run/unresolved-customers/to-clay` | - | Send unresolved customers to Clay |

### Other

| API Endpoint | Modal Function | Description |
|-------------|----------------|-------------|
| `POST /run/linkedin/job-video/ingest` | `ingest-linkedin-job-video` | Ingest LinkedIn job videos |
| `POST /run/IGNORE/IGNORE/IGNORE/process` | `process-similar-companies-queue` | Process similar companies queue |
| `POST /run/testing/companies` | - | Testing endpoint |

---

## Other API Endpoints (Non-Modal)

### `/api/companies/*` (45 endpoints)

Query and lookup company data from the database.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/companies/lookup` | GET | Lookup company by domain |
| `/api/companies/{domain}/customers` | GET | Get company customers |
| `/api/companies/{domain}/icp` | GET | Get company ICP |
| `/api/companies/{domain}/similar` | GET | Get similar companies |
| `/api/companies/{domain}/ads` | GET | Get company ad data |
| `/api/companies/{domain}/customer-insights` | GET | Get customer insights |
| `/api/companies/{domain}/has-customers` | GET | Check has customers |
| `/api/companies/{domain}/has-case-studies` | GET | Check has case studies |
| `/api/companies/by-technology` | GET | Filter by technology |
| `/api/companies/by-job-title` | GET | Filter by job title |
| `/api/companies/by-google-ads` | GET | Filter by Google ads |
| `/api/companies/by-linkedin-ads` | GET | Filter by LinkedIn ads |
| `/api/companies/by-meta-ads` | GET | Filter by Meta ads |
| `/api/companies/check-has-customers` | POST | Batch check customers |
| `/api/companies/check-has-case-studies` | POST | Batch check case studies |

### `/api/enrichment/*` (7 endpoints)

Manage enrichment workflows and similar company discovery.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/enrichment/workflows` | GET | List all workflows |
| `/api/enrichment/workflows/summary` | GET | Workflow summary stats |
| `/api/enrichment/similar-companies/pending` | GET | Pending similar company jobs |
| `/api/enrichment/similar-companies/batch` | POST | Start batch similar company job |
| `/api/enrichment/similar-companies/batch/{id}/status` | GET | Get batch job status |
| `/api/enrichment/similar-companies/queue/status` | GET | Queue status |
| `/api/enrichment/builtwith` | POST | Trigger BuiltWith enrichment |

### `/api/workflows/*` (8 endpoints)

Data resolution and normalization workflows.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows/normalize` | POST | Normalize company name |
| `/api/workflows/resolve-company-name` | POST | Resolve company name |
| `/api/workflows/resolve-domain-from-linkedin` | POST | Get domain from LinkedIn URL |
| `/api/workflows/resolve-domain-from-email` | POST | Get domain from email |
| `/api/workflows/resolve-linkedin-from-domain` | POST | Get LinkedIn from domain |
| `/api/workflows/resolve-person-linkedin-from-email` | POST | Get person LinkedIn from email |
| `/api/workflows/resolve-company-location-from-domain` | POST | Get company location |
| `/api/workflows/resolve-person-location-from-linkedin` | POST | Get person location |

### `/api/admin/*` (70 endpoints)

Administrative and backoffice operations.

Key endpoint groups:
- `/api/admin/core/*` - Core table queries
- `/api/admin/extracted/*` - Extracted data queries
- `/api/admin/gaps/*` - Data gap analysis
- `/api/admin/backfill/*` - Backfill operations
- `/api/admin/top-vc-portfolio/*` - VC portfolio management

### `/api/leads/*` (12 endpoints)

Lead management operations.

### `/api/filters/*` (10 endpoints)

Filter and search operations for the frontend.

### `/api/views/*` (2 endpoints)

Target client view management.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/views` | POST | Create target client view |
| `/api/views/{slug}` | GET | Get view by slug |

---

## Modal Functions Not Yet Wrapped

The following Modal functions exist but don't have corresponding `/run/*` API endpoints:

| Modal Function | Description |
|----------------|-------------|
| `analyze-sec-10k` | Analyze SEC 10-K filings |
| `analyze-sec-10q` | Analyze SEC 10-Q filings |
| `analyze-sec-8k-executive` | Analyze SEC 8-K executive filings |
| `command-center-email-enrichment` | Email enrichment for command center |
| `create-target-client-view` | Create target client view |
| `discover-g2-page-gemini-search` | Discover G2 page via search |
| `discover-g2-page-gemini` | Discover G2 page |
| `discover-pricing-page-url` | Discover pricing page URL |
| `extract-case-study-buyer` | Extract case study buyer info |
| `fetch-meta-description` | Fetch meta description |
| `find-similar-companies-batch` | Batch similar company discovery |
| `find-similar-companies-single` | Single similar company discovery |
| `generate-target-client-icp` | Generate target client ICP |
| `get-company-customers-status` | Get customer discovery status |
| `get-email-job` | Get email enrichment job status |
| `ingest-competitors` | Ingest competitor data |
| `ingest-g2-page-scrape-zenrows` | Scrape G2 pages via ZenRows |
| `ingest-staffing-parallel-search` | Parallel staffing search |
| `my-function` | Test function |
| `read-db-check-existence` | Check DB record existence |
| `search-parallel-ai` | Parallel AI search |
| `test-endpoint` | Test endpoint |
| `your-endpoint` | Template endpoint |

---

## Database Connection

All API endpoints connect to Supabase PostgreSQL:

```
postgresql://postgres:***@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres
```

---

## Deployment

- **API (Railway):** Auto-deploys on push to `main` branch
- **Modal Functions:** `cd modal-functions && uv run modal deploy src/app.py`

---

*This file is auto-maintained. Last sync: 2026-02-16*
