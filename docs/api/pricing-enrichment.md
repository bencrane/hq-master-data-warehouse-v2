# Pricing & Website Enrichment Endpoints

**Created:** 2026-01-31
**Status:** Deployed to Modal, API endpoints pending

## Overview

This document covers the Gemini-powered enrichment endpoints that analyze company pricing pages and websites to extract structured signals for sales targeting.

## Related Documentation

- **Data Ingestion Protocol:** `/docs/DATA_INGESTION_PROTOCOL.md` - The 4-layer schema pattern (raw → extracted → reference → core)
- **Modal App Entry Point:** `/modal-functions/src/app.py` - All endpoints must be imported here
- **Config:** `/modal-functions/src/config.py` - Shared Modal app and image configuration

## Schema Pattern

All enrichment endpoints follow the 3-layer pattern (no reference table needed for these):

1. **raw.{table}_payloads** - Stores the original request/payload
2. **extracted.company_{table}** - Stores extracted data with raw_payload_id FK
3. **core.company_{table}** - Upserted summary keyed by domain

## Deployment

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-functions
uv run modal deploy src/app.py
```

**Important:** Function names that are too long get truncated with a hash. Keep names under ~35 chars.

---

## Pricing Page Enrichments

These endpoints require `pricing_page_url` in the payload.

### Payload Format
```json
{
  "company_name": "Example Inc",
  "domain": "example.com",
  "pricing_page_url": "https://example.com/pricing"
}
```

### Endpoints

| Signal | Endpoint | Values | Description |
|--------|----------|--------|-------------|
| sales_motion | `infer-sales-motion` | self_serve / sales_led / hybrid | How customers buy |
| contact_sales_cta | (included in sales_motion) | yes / no | Has "Contact Sales" CTA |
| free_trial | `infer-free-trial` | yes / no / demo_only | Free trial availability |
| pricing_visibility | `infer-pricing-visibility` | public / hidden / partial | Is pricing shown |
| pricing_model | `infer-pricing-model` | seat_based / usage_based / flat / tiered / custom / multiple | How they charge |
| billing_default | `infer-billing-default` | monthly / annual / both_annual_emphasized / both_monthly_emphasized | Default billing period |
| number_of_tiers | `infer-number-of-tiers` | 1 / 2 / 3 / 4+ | Count of pricing tiers |
| add_ons_offered | `infer-add-ons-offered` | yes / no / unclear | Optional extras available |
| enterprise_tier_exists | `infer-enterprise-tier-exists` | yes / no | Has enterprise tier |
| security_gating | `infer-security-gating` | yes / no / not_mentioned | Security features gated to higher tiers |
| annual_commitment | `infer-annual-commitment` | yes / no / unclear | Requires annual commitment |
| plan_naming_style | `infer-plan-naming-style` | generic / persona_based / feature_based / other | How tiers are named |
| custom_pricing_mentioned | `infer-custom-pricing-mentioned` | yes / no | Has custom pricing option |
| money_back_guarantee | `infer-money-back-guarantee` | yes / no | Offers refund guarantee |
| minimum_seats | `infer-minimum-seats` | yes / no / not_mentioned | Requires minimum seats |

### Full Endpoint URLs

Base: `https://bencrane--hq-master-data-ingest-{endpoint}.modal.run`

Examples:
- `https://bencrane--hq-master-data-ingest-infer-sales-motion.modal.run`
- `https://bencrane--hq-master-data-ingest-infer-free-trial.modal.run`
- `https://bencrane--hq-master-data-ingest-infer-pricing-visibility.modal.run`

---

## Domain-Only Enrichments (Rich Extraction)

These endpoints only require `domain` - they fetch the homepage and extract detailed data.

### Payload Format
```json
{
  "company_name": "Example Inc",
  "domain": "example.com"
}
```

### Comparison Pages

**Endpoint:** `https://bencrane--hq-master-data-ingest-infer-comparison-page-exists.modal.run`

**File:** `/modal-functions/src/ingest/comparison_page_exists.py`

**Returns:**
```json
{
  "has_comparison_pages": true,
  "comparison_count": 3,
  "comparison_pages": [
    {"url": "/vs-salesforce", "title": "Acme vs Salesforce", "competitor": "Salesforce"}
  ],
  "competitors_mentioned": ["Salesforce", "HubSpot"]
}
```

**Tables:**
- `raw.comparison_page_exists_payloads`
- `extracted.company_comparison_pages` (one row per comparison page)
- `core.company_comparison_pages` (summary with has_comparison_pages, comparison_count, competitors_mentioned[])

### Webinars

**Endpoint:** `https://bencrane--hq-master-data-ingest-infer-webinars.modal.run`

**File:** `/modal-functions/src/ingest/webinars.py`

**Logic:** Two-step fetch:
1. Find webinar page URL from homepage
2. Fetch webinar page and extract actual webinar titles/topics

**Returns:**
```json
{
  "has_webinars": true,
  "webinar_count": 5,
  "webinars": [
    {"title": "How to Scale Customer Support with AI", "topic": "AI"}
  ],
  "webinar_topics": ["AI", "Sales", "Customer Success"]
}
```

**Tables:**
- `raw.webinars_payloads`
- `extracted.company_webinars` (one row per webinar)
- `core.company_webinars` (summary with has_webinars, webinar_count, webinar_topics[])

---

## Database Tables Created

All tables exist in Supabase: `postgresql://postgres:***@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres`

### Core Tables (for querying/filtering)
- `core.company_sales_motion` (includes contact_sales_cta)
- `core.company_free_trial`
- `core.company_pricing_visibility`
- `core.company_pricing_model`
- `core.company_billing_default`
- `core.company_number_of_tiers`
- `core.company_add_ons_offered`
- `core.company_enterprise_tier_exists`
- `core.company_security_compliance_gating`
- `core.company_annual_commitment_required`
- `core.company_plan_naming_style`
- `core.company_custom_pricing_mentioned`
- `core.company_money_back_guarantee`
- `core.company_minimum_seats`
- `core.company_comparison_pages`
- `core.company_webinars`

---

## Pending Work: API Endpoints

Need to create FastAPI endpoints in `/hq-api/routers/companies.py` for frontend filtering:

### Option 1: Individual filter endpoints
```
GET /api/companies/by-sales-motion?value=self_serve
GET /api/companies/by-free-trial?value=yes
GET /api/companies/by-webinars  # has_webinars=true
```

### Option 2: Combined filter endpoint
```
GET /api/companies?sales_motion=self_serve&free_trial=yes&has_webinars=true
```

### Option 3: Company detail endpoints
```
GET /api/companies/{domain}/pricing-signals  # all pricing data for a company
GET /api/companies/{domain}/webinars         # webinar details
GET /api/companies/{domain}/comparison-pages # competitor comparison data
```

---

## File Locations

### Modal Ingest Endpoints
All in `/modal-functions/src/ingest/`:
- `sales_motion.py`
- `free_trial.py`
- `pricing_visibility.py`
- `pricing_model.py`
- `billing_default.py`
- `number_of_tiers.py`
- `add_ons_offered.py`
- `enterprise_tier_exists.py`
- `security_compliance_gating.py` (function renamed to `infer_security_gating`)
- `annual_commitment_required.py` (function renamed to `infer_annual_commitment`)
- `plan_naming_style.py`
- `custom_pricing_mentioned.py`
- `money_back_guarantee.py`
- `minimum_seats.py`
- `comparison_page_exists.py`
- `webinars.py`

### App Registration
All endpoints imported in `/modal-functions/src/app.py`

### API Router
Ads endpoints already exist in `/hq-api/routers/companies.py`:
- `GET /api/companies/by-google-ads`
- `GET /api/companies/by-linkedin-ads`
- `GET /api/companies/by-meta-ads`
- `GET /api/companies/{domain}/ads`

---

## Technical Notes

1. **Gemini Model:** All endpoints use `gemini-3-flash-preview`
2. **Timeout:** 60 seconds per request
3. **Page text limit:** 8000 chars (truncated to avoid token limits)
4. **Modal Secrets Required:**
   - `supabase-credentials` (SUPABASE_URL, SUPABASE_SERVICE_KEY)
   - `gemini-secret` (GEMINI_API_KEY)

5. **URL Length:** Modal truncates function names >~40 chars with a hash. We renamed:
   - `infer_security_compliance_gating` → `infer_security_gating`
   - `infer_annual_commitment_required` → `infer_annual_commitment`

---

## Other Enrichments Built in This Session

### Ad Platform Data (Adyntel)
- LinkedIn Ads: `ingest-linkedin-ads`
- Google Ads: `ingest-google-ads`
- Meta Ads: `ingest-meta-ads`

See existing ads API endpoints in `/hq-api/routers/companies.py`.
