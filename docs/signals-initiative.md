# Signals Initiative

> **Status:** In Progress  
> **Started:** 2026-01-21  
> **Last Updated:** 2026-01-21

---

## Overview

Signals are event-driven intelligence derived from monitored companies and people. Clay detects these signals and sends payloads to Modal endpoints, which store raw data and extract normalized records for querying.

**Architecture:**
```
Clay Signal → Modal Ingest Endpoint → raw.clay_* table → extraction → extracted.clay_* table
```

---

## Infrastructure

### Signal Registry

All signals are registered in `reference.signal_registry`:

| Column | Purpose |
|--------|---------|
| `signal_slug` | Unique identifier (e.g., `clay-new-hire`) |
| `signal_level` | `company` or `person` |
| `signal_category` | `hiring`, `funding`, `job_change`, `promotion`, etc. |
| `source` | `clay`, `custom`, `crm` |
| `required_inputs` | JSONB - fields needed to monitor |
| `output_fields` | JSONB - fields the signal produces |
| `is_active` | Enable/disable signals |

---

## Completed Signals

### 1. New Hire (Company)

**Signal Slug:** `clay-new-hire`

**Endpoint:**
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-signal-new-hire.modal.run
```

**Payload:**
```json
{
  "company_domain": "acme.com",
  "company_linkedin_url": "https://linkedin.com/company/acme",
  "company_name": "Acme Corp",
  "person_linkedin_url": "https://linkedin.com/in/johndoe",
  "signal_slug": "clay-new-hire",
  "clay_table_url": "https://app.clay.com/..."
}
```

**Tables:**
- `raw.clay_new_hire_payloads`
- `extracted.clay_new_hire`

---

### 2. News & Fundraising (Company)

**Signal Slug:** `clay-news-fundraising`

**Endpoint:**
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-signal-news--9963a4.modal.run
```

**Payload:**
```json
{
  "company_domain": "microsoft.com",
  "raw_event_payload": { ... full Clay event object ... },
  "news_url": "https://...",
  "news_title": "...",
  "description": "...",
  "signal_slug": "clay-news-fundraising",
  "clay_table_url": "https://app.clay.com/..."
}
```

**Notes:**
- `publish_date` extracted from `raw_event_payload.newsData.publishDate` (ISO format)
- Full Clay event stored for auditability

**Tables:**
- `raw.clay_news_fundraising_payloads`
- `extracted.clay_news_fundraising`

---

### 3. Job Posting (Company)

**Signal Slug:** `clay-job-posting`

**Endpoint:**
```
POST https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-posting.modal.run
```

**Payload:**
```json
{
  "company_linkedin_url": "https://linkedin.com/company/google",
  "company_record_raw_payload": { ... company record object ... },
  "company_name": "Google",
  "job_title": "Senior Software Engineer",
  "location": "San Francisco, CA",
  "company_domain": "google.com",
  "job_linkedin_url": "https://linkedin.com/jobs/view/123456",
  "post_on": "2026-01-15",
  "signal_slug": "clay-job-posting",
  "clay_table_url": "https://app.clay.com/..."
}
```

**Notes:**
- `company_record_raw_payload` stores full company record for reference
- `post_on` date parsing has known issues (revisit)

**Tables:**
- `raw.clay_job_posting_payloads`
- `extracted.clay_job_posting`

---

## Remaining Signals

| Signal | Level | Slug | Notes |
|--------|-------|------|-------|
| Web Intent | Company | `clay-web-intent` | Presignal/trigger |
| Job Change | Person | `clay-job-change` | |
| Promotion | Person | `clay-promotion` | |
| LinkedIn Post Brand Mentions | Person | `clay-linkedin-brand-mention` | Spec TBD |

---

## File Structure

```
modal-mcp-server/src/
├── ingest/
│   ├── signal_new_hire.py
│   ├── signal_news_fundraising.py
│   └── signal_job_posting.py
└── extraction/
    ├── signal_new_hire.py
    ├── signal_news_fundraising.py
    └── signal_job_posting.py

supabase/migrations/
├── 20260121_signal_registry.sql
├── 20260121_clay_signal_new_hire.sql
├── 20260121_clay_signal_news_fundraising.sql
└── 20260121_clay_signal_job_posting.sql

signals/
├── companies/clay/
│   ├── job-posting.md
│   ├── new-hire.md
│   ├── news-and-fundraising.md
│   └── web-intent.md
└── people/clay/
    ├── job-change.md
    ├── promotion.md
    └── linkedin-post-brand-mentions.md
```

---

## Known Issues

1. **Date parsing** - `post_on` field in Job Posting signal not parsing correctly. Clay sends dates in a format that doesn't match expected patterns. Workaround: format in Clay or extract from raw payload.

---

## Next Steps

1. Build remaining 4 signals (Web Intent, Job Change, Promotion, LinkedIn Brand Mentions)
2. Replicate signal infrastructure to `outbound-solutions-db` (Option B: separate endpoints per DB)
3. Build signal feed UI for clients
