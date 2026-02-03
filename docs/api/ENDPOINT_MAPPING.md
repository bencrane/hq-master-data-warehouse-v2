# Endpoint Mapping

Maps Modal serverless functions to their API wrapper endpoints at `api.revenueinfra.com`.

## Convention

| Component | Pattern |
|-----------|---------|
| Modal function | `ingest_clay_find_companies` |
| Modal URL | `https://bencrane--hq-master-data-ingest-{function-name}.modal.run` |
| API endpoint | `POST /api/ingest/companies/{action}` |

---

## Mappings

| Workflow Slug | Modal Function | Modal Endpoint URL | API Endpoint |
|---------------|----------------|-------------------|--------------|
| clay-company-firmographics | ingest_clay_company_firmo | https://bencrane--hq-master-data-ingest-ingest-clay-company-firmo.modal.run | POST /run/companies/clay-native/firmographics/ingest |
| clay-find-companies | ingest_clay_find_companies | https://bencrane--hq-master-data-ingest-ingest-clay-find-companies.modal.run | POST /run/companies/clay-native/find-companies/ingest |
| clay-find-people | ingest_clay_find_people | https://bencrane--hq-master-data-ingest-ingest-clay-find-people.modal.run | POST /run/people/clay-native/find-people/ingest |
| company-classification | ingest_company_classification | https://bencrane--hq-master-data-ingest-ingest-company-classification.modal.run | POST /run/companies/gemini/type-classification/ingest |
| infer-annual-commitment-required | infer_annual_commitment | https://bencrane--hq-master-data-ingest-infer-annual-commitment.modal.run | POST /run/companies/gemini/annual-commitment/infer |
| infer-billing-default | infer_billing_default | https://bencrane--hq-master-data-ingest-infer-billing-default.modal.run | POST /run/companies/gemini/billing-default/infer |
| infer-company-country | infer_company_country | https://bencrane--hq-master-data-ingest-infer-company-country.modal.run | POST /run/companies/gemini/country/infer |
| infer-company-employee-range | infer_company_employee_range | https://bencrane--hq-master-data-ingest-infer-company-employee-range.modal.run | POST /run/companies/gemini/employee-range/infer |
| infer-company-industry | infer_company_industry | https://bencrane--hq-master-data-ingest-infer-company-industry.modal.run | POST /run/companies/gemini/industry/infer |
| infer-company-linkedin-url | infer_company_linkedin_url | https://bencrane--hq-master-data-ingest-infer-company-linkedin-url.modal.run | POST /run/companies/gemini/linkedin-url/get |
| infer-comparison-page-exists | infer_comparison_page_exists | https://bencrane--hq-master-data-ingest-infer-comparison-page-exists.modal.run | POST /run/companies/gemini/comparison-page-check/infer |
| gemini-crunchbase-domain-inference | infer_crunchbase_domain | https://bencrane--hq-master-data-ingest-infer-crunchbase-domain.modal.run | POST /run/companies/gemini/crunchbase-url/get |
| infer-enterprise-tier-exists | infer_enterprise_tier_exists | https://bencrane--hq-master-data-ingest-infer-enterprise-tier-exists.modal.run | POST /run/companies/gemini/enterprise-tier-check/infer |
| infer-free-trial | infer_free_trial | https://bencrane--hq-master-data-ingest-infer-free-trial.modal.run | POST /run/companies/gemini/free-trial-check/infer |
| infer-minimum-seats | infer_minimum_seats | https://bencrane--hq-master-data-ingest-infer-minimum-seats.modal.run | POST /run/companies/gemini/min-seats-check/infer |
| infer-money-back-guarantee | infer_money_back_guarantee | https://bencrane--hq-master-data-ingest-infer-money-back-guarantee.modal.run | POST /run/companies/gemini/money-back-check/infer |
| infer-number-of-tiers | infer_number_of_tiers | https://bencrane--hq-master-data-ingest-infer-number-of-tiers.modal.run | POST /run/companies/gemini/tier-number-check/infer |
| infer-plan-naming-style | infer_plan_naming_style | https://bencrane--hq-master-data-ingest-infer-plan-naming-style.modal.run | POST /run/companies/gemini/plan-naming-check/infer |
| infer-pricing-model | infer_pricing_model | https://bencrane--hq-master-data-ingest-infer-pricing-model.modal.run | POST /run/companies/gemini/pricing-model-check/infer |
| infer-pricing-visibility | infer_pricing_visibility | https://bencrane--hq-master-data-ingest-infer-pricing-visibility.modal.run | POST /run/companies/gemini/pricing-visibility-check/infer |
| infer-sales-motion | infer_sales_motion | https://bencrane--hq-master-data-ingest-infer-sales-motion.modal.run | POST /run/companies/gemini/sales-motion-check/infer |
| infer-security-gating | infer_security_gating | https://bencrane--hq-master-data-ingest-infer-security-gating.modal.run | POST /run/companies/gemini/security-gating-check/infer |
| infer-webinars | infer_webinars | https://bencrane--hq-master-data-ingest-infer-webinars.modal.run | POST /run/companies/gemini/webinars-status-data/infer |
| leadmagic-company-enrichment | ingest_leadmagic_company | https://bencrane--hq-master-data-ingest-ingest-leadmagic-company.modal.run | POST /run/companies/clay-leadmagic/enrich/ingest |
| linkedin-ads-ingest | ingest_linkedin_ads | https://bencrane--hq-master-data-ingest-ingest-linkedin-ads.modal.run | POST /run/companies/clay-adyntel/linkedin-ads/ingest |
| meta-ads-ingest | ingest_meta_ads | https://bencrane--hq-master-data-ingest-ingest-meta-ads.modal.run | POST /run/companies/clay-adyntel/meta-ads/ingest |
| google-ads-ingest | ingest_google_ads | https://bencrane--hq-master-data-ingest-ingest-google-ads.modal.run | POST /run/companies/clay-adyntel/google-ads/ingest |
| predictleads-techstack | ingest_predictleads_techstack | https://bencrane--hq-master-data-ingest-ingest-predictleads-techstack.modal.run | POST /run/companies/clay-predictleads/get-tech-stack/ingest |
| builtwith-techstack | ingest_builtwith | https://bencrane--hq-master-data-ingest-ingest-builtwith.modal.run | POST /run/companies/built-with/site-tech/ingest |
| has-raised-vc | has_raised_vc | https://bencrane--hq-master-data-ingest-has-raised-vc.modal.run | POST /run/companies/db/has-raised-vc-status/check |
| infer-add-ons-offered | infer_add_ons_offered | https://bencrane--hq-master-data-ingest-infer-add-ons-offered.modal.run | POST /run/companies/gemini/add-ons-offered/infer |
| clay-cleaned-company-name | ingest_cleaned_company_name | https://bencrane--hq-master-data-ingest-ingest-cleaned-company-name.modal.run | POST /run/companies/clay-native/normalize-company/ingest |
| anymailfinder-email | ingest_email_anymailfinder | https://bencrane--hq-master-data-ingest-ingest-email-anymailfinder.modal.run | POST /run/people/clay-anymail/get-email/ingest |
| icypeas-email | ingest_email_icypeas | https://bencrane--hq-master-data-ingest-ingest-email-icypeas.modal.run | POST /run/people/clay-icypeas/get-email/ingest |
| leadmagic-email | ingest_email_leadmagic | https://bencrane--hq-master-data-ingest-ingest-email-leadmagic.modal.run | POST /run/people/clay-leadmagic/get-email/ingest |
| icp-fit-criterion | ingest_icp_fit_criterion | https://bencrane--hq-master-data-ingest-ingest-icp-fit-criterion.modal.run | POST /run/companies/gemini/icp-fit-criterion/ingest |
| icp-industries | ingest_icp_industries | https://bencrane--hq-master-data-ingest-ingest-icp-industries.modal.run | POST /run/companies/gemini/icp-industries/ingest |
| icp-job-titles | ingest_icp_job_titles | https://bencrane--hq-master-data-ingest-ingest-icp-job-titles.modal.run | POST /run/companies/gemini/icp-job-titles/ingest |
| icp-value-proposition | ingest_icp_value_proposition | https://bencrane--hq-master-data-ingest-ingest-icp-value-proposition.modal.run | POST /run/companies/gemini/icp-value-prop/ingest |
| icp-verdict-enrichment | ingest_icp_verdict | https://bencrane--hq-master-data-ingest-ingest-icp-verdict.modal.run | POST /run/companies/gemini/icp-verdict/ingest |
| job-posting | ingest_job_posting | https://bencrane--hq-master-data-ingest-ingest-job-posting.modal.run | POST /run/companies/gemini/icp-job-posting/ingest |
| manual-company-customers | ingest_manual_comp_customer | https://bencrane--hq-master-data-ingest-ingest-manual-comp-customer.modal.run | POST /run/companies/manual/customers/ingest |
| company-public | ingest_public_company | https://bencrane--hq-master-data-ingest-ingest-public-company.modal.run | POST /run/companies/manual/public-company-check/ingest |
| core-company-simple | ingest_core_company_simple | https://bencrane--hq-master-data-ingest-ingest-core-company-simple.modal.run | POST /run/companies/manual/core-data/ingest |
| case-study-buyers | ingest_case_study_buyers | https://bencrane--hq-master-data-ingest-ingest-case-study-buyers.modal.run | POST /run/companies/not-sure/case-study-buyers/ingest |
| gemini-extract-case-study-details | ingest_case_study_extraction | https://bencrane--hq-master-data-ingest-ingest-case-study-extraction.modal.run | POST /run/companies/gemini/case-study-extraction/ingest |
| salesnav-company | ingest_salesnav_company | https://bencrane--hq-master-data-ingest-ingest-salesnav-company.modal.run | POST /run/companies/salesnav/scraped-data/ingest |
| salesnav-person | ingest_salesnav_person | https://bencrane--hq-master-data-ingest-ingest-salesnav-person.modal.run | POST /run/people/salesnav/scraped-data/ingest |
| signal-job-change-v2 | ingest_signal_job_change | https://bencrane--hq-master-data-ingest-ingest-signal-job-change.modal.run | POST /run/people/clay-native/signal-job-change/ingest |
| signal-job-posting-v2 | ingest_signal_job_posting | https://bencrane--hq-master-data-ingest-ingest-signal-job-posting.modal.run | POST /run/people/clay-native/signal-job-posting/ingest |
| signal-promotion-v2 | ingest_signal_promotion | https://bencrane--hq-master-data-ingest-ingest-signal-promotion.modal.run | POST /run/people/clay-native/signal-promotion/ingest |
| vc-portfolio | ingest_cb_vc_portfolio | https://bencrane--hq-master-data-ingest-ingest-cb-vc-portfolio.modal.run | POST /run/companies/cb/vc-portfolio/ingest |
| clay-company-vc-investors | ingest_company_vc_investors | https://bencrane--hq-master-data-ingest-ingest-company-vc-investors.modal.run | POST /run/companies/cb/company-investors/ingest |
| claygent-get-all-company-customers | ingest_all_comp_customers | https://bencrane--hq-master-data-ingest-ingest-all-comp-customers.modal.run | POST /run/companies/claygent/customers-of-1/ingest |
| company-customers-v2 | ingest_company_customers_v2 | https://bencrane--hq-master-data-ingest-ingest-company-customers-v2.modal.run | POST /run/companies/claygent/customers-of-2/ingest |
| company-customers-structured | ingest_company_customers_structured | https://bencrane--hq-master-data-ingest-ingest-company-customers-85468a.modal.run | POST /run/companies/claygent/customers-of-3/ingest |
| company-customers-claygent | ingest_company_customers_claygent | https://bencrane--hq-master-data-ingest-ingest-company-customers-a12938.modal.run | POST /run/companies/claygent/customers-of-4/ingest |
| company-address-parsing | ingest_company_address_parsing | https://bencrane--hq-master-data-ingest-ingest-company-address-parsing.modal.run | POST /run/companies/claygent/company-address-parsing/ingest |
| lookup-company-customers | lookup_company_customers | https://bencrane--hq-master-data-ingest-lookup-company-customers.modal.run | POST /run/companies/db/company-customers/lookup |
| lookup-company-icp | lookup_company_icp | https://bencrane--hq-master-data-ingest-lookup-company-icp.modal.run | POST /run/companies/db/company-icp/lookup |
| lookup-job-title | lookup_job_title | https://bencrane--hq-master-data-ingest-lookup-job-title.modal.run | POST /run/people/db/person-job-title/lookup |
| lookup-person-location | lookup_person_location | https://bencrane--hq-master-data-ingest-lookup-person-location.modal.run | POST /run/people/db/person-location/lookup |
| clay-signal-job-change | ingest_clay_signal_job_change | https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-change.modal.run | POST /run/people/clay-native/signal-job-change-2/ingest |
| clay-person-profile | ingest_clay_person_profile | https://bencrane--hq-master-data-ingest-ingest-clay-person-profile.modal.run | POST /run/people/clay-native/person-profile/ingest |
| clay-signal-job-posting | ingest_clay_signal_job_posting | https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-posting.modal.run | POST /run/companies/clay-native/signal-job-posting-2/ingest |
| clay-signal-new-hire | ingest_clay_signal_new_hire | https://bencrane--hq-master-data-ingest-ingest-clay-signal-new-hire.modal.run | POST /run/people/clay-native/signal-new-hire-2/ingest |
| clay-signal-promotion | ingest_clay_signal_promotion | https://bencrane--hq-master-data-ingest-ingest-clay-signal-promotion.modal.run | POST /run/people/clay-native/signal-promotion-2/ingest |
| clay-find-people-title-enrichment | ingest_ppl_title_enrich | https://bencrane--hq-master-data-ingest-ingest-ppl-title-enrich.modal.run | POST /run/people/not-sure/job-title-clean/ingest |
| salesnav-company-location-lookup | lookup_salesnav_company_location | https://bencrane--hq-master-data-ingest-lookup-salesnav-company--1838bd.modal.run | POST /run/companies/db/salesnav-company-location/lookup |
| salesnav-person-location-lookup | lookup_salesnav_location | https://bencrane--hq-master-data-ingest-lookup-salesnav-location.modal.run | POST /run/--/db/salesnav-person/lookup |

---

*This file is updated alongside the workflow registry whenever new API wrappers are created.*
