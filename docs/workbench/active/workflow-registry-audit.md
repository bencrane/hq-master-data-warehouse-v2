# Workflow Registry Audit

**Status:** NOT STARTED - Table does not exist
**Goal:** Register all Modal endpoints in `reference.enrichment_workflow_registry`

---

## ⚠️ CRITICAL: Table Does Not Exist

**The `reference.enrichment_workflow_registry` table does NOT exist in the database.**

Previous documentation claimed 106 workflows were registered, but this was incorrect. The table needs to be created from scratch.

Query to verify:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'reference';
-- Returns only: countries
```

---

## Current State

- **Table exists:** NO
- **Registered:** 0 workflows
- **Modal ingest functions:** ~87 files in `/modal-functions/src/ingest/`

### By Entity Type
| Entity Type | Total | Has Raw Table | Coalesces to Core |
|-------------|-------|---------------|-------------------|
| company | 75 | 48 | 20 |
| person | 24 | 16 | 7 |
| target_client | 7 | 4 | 3 |

---

## Registry Schema

| Column | Type | Description |
|--------|------|-------------|
| workflow_slug | text | Unique identifier (e.g., "clay-company-firmographics") |
| provider | text | Data source (clay, apollo, salesnav, leadmagic, etc.) |
| platform | text | Execution platform (clay, modal, gemini) |
| payload_type | text | Type of data (discovery, enrichment, signal, inference) |
| entity_type | text | company, person, or target_client |
| description | text | Human-readable description |
| raw_table | text | Table in raw schema |
| extracted_table | text | Table in extracted schema |
| core_table | text | Table in core schema (if coalesces) |
| modal_function_name | text | Python function name in Modal |
| coalesces_to_core | boolean | Whether data flows to core schema |
| is_active | boolean | Whether workflow is currently in use |

---

## Endpoints to Register

### Company Workflows

| Function Name | Suggested Slug | Provider | Payload Type | Raw Table | Active |
|--------------|----------------|----------|--------------|-----------|--------|
| ingest_clay_company_firmo | clay-company-firmographics | clay | firmographics | raw.company_payloads | ✓ REGISTERED |
| ingest_clay_find_companies | clay-find-companies | clay | discovery | raw.company_discovery | ✓ REGISTERED |
| ingest_clay_find_co_lctn_prsd | clay-find-companies-location-parsed | clay | discovery | raw.company_discovery | ✓ REGISTERED |
| ingest_all_comp_customers | claygent-get-all-company-customers | clay | customer_research | raw.company_customer_claygent_payloads | ✓ REGISTERED |
| ingest_manual_comp_customer | manual-company-customers | manual | customer_research | raw.company_customer_claygent_payloads | ✓ REGISTERED |
| upsert_core_company | upsert-core-company | internal | upsert | - | core.companies | NEW |
| ingest_company_address_parsing | company-address-parsing | clay | enrichment | raw.company_address_payloads | NEW |
| ingest_salesnav_company | salesnav-company | salesnav | enrichment | raw.salesnav_company_payloads | NEW |
| ingest_leadmagic_company | leadmagic-company | leadmagic | enrichment | raw.leadmagic_company_payloads | NEW |
| ingest_company_customers_claygent | company-customers-claygent | clay | customer_research | raw.company_customers_claygent | NEW |
| ingest_company_customers_structured | company-customers-structured | clay | customer_research | raw.company_customers_structured | NEW |
| ingest_company_customers_v2 | company-customers-v2 | clay | customer_research | raw.claygent_customers_v2_raw | NEW |
| ingest_public_company | company-public | internal | enrichment | - | NEW |
| ingest_core_company_simple | core-company-simple | internal | upsert | - | core.companies | NEW |
| upsert_core_company_full | upsert-core-company-full | internal | upsert | - | core.companies_full | NEW |
| ingest_company_vc_investors | clay-company-vc-investors | clay | enrichment | raw.company_vc_investors | ✓ REGISTERED |
| ingest_vc_portfolio | vc-portfolio | clay | enrichment | raw.vc_portfolio_payloads | NEW |
| ingest_cb_vc_portfolio | cb-vc-portfolio | crunchbase | enrichment | raw.cb_vc_portfolio_payloads | NEW |
| lookup_vc_domain | vc-domain-lookup | internal | lookup | - | NEW |
| update_vc_domain | vc-domain-update | internal | upsert | - | NEW |
| has_raised_vc | has-raised-vc | internal | inference | - | NEW |
| ingest_apollo_scrape | apollo-scrape | apollo | enrichment | raw.apollo_scrape | NEW |
| ingest_apollo_companies_cleaned | apollo-companies-cleaned | apollo | enrichment | raw.apollo_companies_cleaned | NEW |
| ingest_nostra_ecom_company | nostra-ecom-company | nostra | enrichment | raw.nostra_ecom_company | NEW |
| ingest_cleaned_company_name | cleaned-company-name | clay | enrichment | raw.clay_cleaned_company_names | NEW |
| ingest_case_study_extraction | gemini-extract-case-study-details | google | case_study_extraction | raw.case_study_extraction_payloads | ✓ REGISTERED |
| ingest_case_study_buyers | case-study-buyers | google | case_study_extraction | raw.case_study_buyers_payloads | NEW |
| extract_case_study_buyer | extract-case-study-buyer | google | extraction | - | NEW |
| find_similar_companies_batch | company-enrich-similar-batch | harmonic | enrichment | raw.company_enrich_similar | NEW |
| find_similar_companies_single | company-enrich-similar-single | harmonic | enrichment | raw.company_enrich_similar | NEW |
| ingest_builtwith | builtwith-techstack | builtwith | enrichment | raw.builtwith_payloads | NEW |
| ingest_predictleads_techstack | predictleads-techstack | predictleads | enrichment | raw.predictleads_techstack | NEW |
| ingest_job_posting | job-posting | clay | signal | raw.job_posting_payloads | NEW |
| ingest_company_classification | company-classification | internal | enrichment | raw.company_classification | NEW |
| ingest_linkedin_ads | linkedin-ads | clay | enrichment | raw.linkedin_ads_payloads | NEW |
| ingest_google_ads | google-ads | clay | enrichment | raw.google_ads_payloads | NEW |
| ingest_meta_ads | meta-ads | clay | enrichment | raw.meta_ads_payloads | NEW |

### Company Inference Workflows

| Function Name | Suggested Slug | Provider | Payload Type | Active |
|--------------|----------------|----------|--------------|--------|
| infer_crunchbase_domain | gemini-crunchbase-domain-inference | google | domain_inference | ✓ REGISTERED |
| infer_company_country | infer-company-country | gemini | inference | NEW |
| infer_company_industry | infer-company-industry | gemini | inference | NEW |
| infer_company_employee_range | infer-company-employee-range | gemini | inference | NEW |
| infer_company_linkedin_url | infer-company-linkedin-url | gemini | inference | NEW |
| fetch_meta_description | fetch-meta-description | internal | extraction | NEW |
| update_staging_company_linkedin | staging-company-linkedin-update | internal | upsert | NEW |

### Pricing/Sales Motion Inference (Company)

| Function Name | Suggested Slug | Provider | Payload Type | Raw Table | Active |
|--------------|----------------|----------|--------------|-----------|--------|
| infer_sales_motion | infer-sales-motion | gemini | inference | raw.sales_motion_payloads | NEW |
| infer_free_trial | infer-free-trial | gemini | inference | raw.free_trial_payloads | NEW |
| infer_pricing_visibility | infer-pricing-visibility | gemini | inference | raw.pricing_visibility_payloads | NEW |
| infer_pricing_model | infer-pricing-model | gemini | inference | raw.pricing_model_payloads | NEW |
| infer_billing_default | infer-billing-default | gemini | inference | raw.billing_default_payloads | NEW |
| infer_number_of_tiers | infer-number-of-tiers | gemini | inference | raw.number_of_tiers_payloads | NEW |
| infer_add_ons_offered | infer-add-ons-offered | gemini | inference | raw.add_ons_offered_payloads | NEW |
| infer_enterprise_tier_exists | infer-enterprise-tier-exists | gemini | inference | raw.enterprise_tier_exists_payloads | NEW |
| infer_security_gating | infer-security-compliance-gating | gemini | inference | raw.security_compliance_gating_payloads | NEW |
| infer_annual_commitment | infer-annual-commitment-required | gemini | inference | raw.annual_commitment_required_payloads | NEW |
| infer_plan_naming_style | infer-plan-naming-style | gemini | inference | raw.plan_naming_style_payloads | NEW |
| infer_custom_pricing_mentioned | infer-custom-pricing-mentioned | gemini | inference | raw.custom_pricing_mentioned_payloads | NEW |
| infer_money_back_guarantee | infer-money-back-guarantee | gemini | inference | raw.money_back_guarantee_payloads | NEW |
| infer_comparison_page_exists | infer-comparison-page-exists | gemini | inference | raw.comparison_page_exists_payloads | NEW |
| infer_minimum_seats | infer-minimum-seats | gemini | inference | raw.minimum_seats_payloads | NEW |
| infer_webinars | infer-webinars | gemini | inference | raw.webinars_payloads | NEW |

### Person Workflows

| Function Name | Suggested Slug | Provider | Payload Type | Raw Table | Active |
|--------------|----------------|----------|--------------|-----------|--------|
| ingest_clay_person_profile | clay-person-profile | clay | profile | raw.person_payloads | ✓ REGISTERED |
| ingest_clay_find_people | clay-find-people | clay | discovery | raw.person_discovery | ✓ REGISTERED |
| ingest_clay_find_ppl_lctn_prsd | clay-find-people-location-parsed | clay | discovery | raw.person_discovery | ✓ REGISTERED |
| ingest_ppl_title_enrich | clay-find-people-title-enrichment | clay | enrichment | raw.person_payloads | ✓ REGISTERED |
| ingest_salesnav_person | salesnav-person | salesnav | enrichment | raw.salesnav_person_payloads | NEW |
| ingest_apollo_people_cleaned | apollo-people-cleaned | apollo | enrichment | raw.apollo_people_cleaned | NEW |
| ingest_nostra_ecom_person | nostra-ecom-person | nostra | enrichment | raw.nostra_ecom_person | NEW |
| ingest_email_anymailfinder | anymailfinder-email | anymailfinder | enrichment | raw.anymailfinder_email | ✓ REGISTERED |
| ingest_email_leadmagic | leadmagic-email | leadmagic | enrichment | raw.leadmagic_email | ✓ REGISTERED |
| ingest_icp_verdict | icp-verdict-enrichment | clay | icp_verdict | raw.icp_verdict_payloads | ✓ REGISTERED |

### Signal Workflows (Person)

| Function Name | Suggested Slug | Provider | Payload Type | Raw Table | Active |
|--------------|----------------|----------|--------------|-----------|--------|
| ingest_clay_signal_job_change | clay-signal-job-change | clay | signal | raw.signal_job_change | NEW |
| ingest_clay_signal_promotion | clay-signal-promotion | clay | signal | raw.signal_promotion | NEW |
| ingest_clay_signal_new_hire | clay-signal-new-hire | clay | signal | raw.signal_new_hire | NEW |
| ingest_clay_signal_news_fundraising | clay-signal-news-fundraising | clay | signal | raw.signal_news_fundraising | NEW |
| ingest_clay_signal_job_posting | clay-signal-job-posting | clay | signal | raw.signal_job_posting | NEW |
| ingest_signal_job_change | signal-job-change-v2 | clay | signal | raw.signal_job_change_v2 | NEW |
| ingest_signal_promotion | signal-promotion-v2 | clay | signal | raw.signal_promotion_v2 | NEW |
| ingest_signal_job_posting | signal-job-posting-v2 | clay | signal | raw.signal_job_posting_v2 | NEW |

### Lookup Workflows (Internal)

| Function Name | Suggested Slug | Entity Type | Description | Active |
|--------------|----------------|-------------|-------------|--------|
| lookup_person_location | lookup-person-location | person | Location lookup for person | NEW |
| lookup_salesnav_location | lookup-salesnav-location | person | SalesNav location lookup | NEW |
| lookup_salesnav_company_location | lookup-salesnav-company-location | company | SalesNav company location | NEW |
| lookup_job_title | lookup-job-title | person | Job title normalization | NEW |
| lookup_company_name | lookup-company-name | company | Company name lookup | NEW |
| lookup_company_customers | lookup-company-customers | company | Customer lookup | NEW |
| lookup_company_icp | lookup-company-icp | company | ICP criteria lookup | NEW |
| ingest_clay_company_location_lookup | clay-company-location-lookup | company | Clay location ingest | NEW |
| ingest_clay_person_location_lookup | clay-person-location-lookup | person | Clay person location | NEW |

### ICP / Target Client Workflows

| Function Name | Suggested Slug | Entity Type | Description | Active |
|--------------|----------------|-------------|-------------|--------|
| create_target_client_view | create-target-client-view | target_client | Create view | NEW |
| upsert_icp_criteria | upsert-icp-criteria | target_client | Upsert ICP | NEW |
| ingest_icp_industries | icp-industries | target_client | ICP industries | NEW |
| ingest_icp_job_titles | icp-job-titles | target_client | ICP job titles | NEW |
| ingest_icp_value_proposition | icp-value-proposition | target_client | ICP value prop | NEW |
| ingest_icp_fit_criterion | icp-fit-criterion | target_client | ICP fit criteria | NEW |
| generate_target_client_icp | ai-generate-target-client-icp | target_client | AI ICP generation | ✓ REGISTERED |

### Backfill Workflows

| Function Name | Suggested Slug | Entity Type | Description | Active |
|--------------|----------------|-------------|-------------|--------|
| backfill_person_location | backfill-person-location | person | Backfill locations | NEW |
| backfill_person_matched_location | backfill-person-matched-location | person | Match locations | NEW |
| backfill_cleaned_company_name | backfill-cleaned-company-name | company | Clean names | NEW |
| backfill_company_descriptions | backfill-company-descriptions | company | Add descriptions | NEW |

### Utility Workflows

| Function Name | Suggested Slug | Description | Active |
|--------------|----------------|-------------|--------|
| command_center_email_enrichment | email-waterfall | Email enrichment waterfall | NEW |
| get_email_job | email-job-status | Check email job status | NEW |
| get_company_customers_status | company-customers-status | Check customer enrichment | NEW |
| get_similar_companies_batch_status | similar-companies-batch-status | Check batch status | NEW |
| get_similar_companies_queue_status | similar-companies-queue-status | Check queue status | NEW |
| process_similar_companies_queue | similar-companies-queue-process | Process queue | NEW |
| delete_companies_no_location | cleanup-delete-no-location | Delete companies without location | NEW |

---

## Next Steps

1. ~~Review this catalog for accuracy~~ ✓
2. ~~Generate SQL INSERT statements~~ ✓
3. ~~Bulk insert into registry~~ ✓
4. ~~Verify with query~~ ✓
5. **Next:** Build API endpoints for enrichment status visibility (Phase 2)

