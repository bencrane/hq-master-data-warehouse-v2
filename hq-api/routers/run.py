"""
Run Router - API wrappers for Modal serverless functions

This router provides API endpoints that wrap Modal functions,
giving a consistent api.revenueinfra.com interface for all workflows.

Naming convention:
    /run/{entity}/{platform}/{workflow}/{action}

Example:
    POST /run/companies/clay-native/find-companies/ingest
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, List
from db import get_pool

router = APIRouter(prefix="/run", tags=["run"])

# Modal base URL
MODAL_BASE_URL = "https://bencrane--hq-master-data-ingest"


# =============================================================================
# Request/Response Models
# =============================================================================

class CompanyFirmographicsRequest(BaseModel):
    company_domain: str
    workflow_slug: str = "clay-company-firmographics"
    raw_payload: dict


class CompanyDiscoveryRequest(BaseModel):
    company_domain: str
    workflow_slug: str = "clay-find-companies"
    raw_payload: dict
    clay_table_url: Optional[str] = None


class PersonDiscoveryRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str = "clay-find-people"
    raw_payload: dict
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    clay_table_url: Optional[str] = None


class CompanyFirmographicsResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    error: Optional[str] = None


class CompanyDiscoveryResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    mapped_id: Optional[str] = None
    matched_city: Optional[str] = None
    matched_state: Optional[str] = None
    matched_industry: Optional[str] = None


class PersonIngestResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    error: Optional[str] = None
    mapped_id: Optional[str] = None
    matched_city: Optional[str] = None
    matched_state: Optional[str] = None
    matched_seniority: Optional[str] = None
    matched_job_function: Optional[str] = None


class CompanyClassificationRequest(BaseModel):
    domain: str
    classification_payload: dict
    clay_table_url: Optional[str] = None


class CompanyClassificationResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    is_b2b: Optional[bool] = None
    is_b2c: Optional[bool] = None
    error: Optional[str] = None


class PricingInferenceRequest(BaseModel):
    domain: str
    pricing_page_url: str
    company_name: Optional[str] = None


class AnnualCommitmentResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    annual_commitment_required: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class BillingDefaultResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    billing_default: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class CountryInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None


class CountryInferenceResponse(BaseModel):
    success: bool
    company_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class EmployeeRangeInferenceRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None


class EmployeeRangeInferenceResponse(BaseModel):
    success: bool
    company_name: Optional[str] = None
    employee_range: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class IndustryInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    short_description: Optional[str] = None


class IndustryInferenceResponse(BaseModel):
    success: bool
    company_name: Optional[str] = None
    gemini_raw: Optional[list] = None
    matched_industries: Optional[list] = None
    best_match: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class LinkedInUrlInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None


class LinkedInUrlInferenceResponse(BaseModel):
    success: bool
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class ComparisonPageRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None


class ComparisonPageResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    comparison_page_exists: Optional[bool] = None
    comparison_page_url: Optional[str] = None
    explanation: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class CrunchbaseUrlRequest(BaseModel):
    company_name: str
    crunchbase_url: str
    vc_name: Optional[str] = None
    vc_domain: Optional[str] = None
    investment_round: Optional[str] = None
    workflow_slug: str = "gemini-crunchbase-domain-inference"


class CrunchbaseUrlResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    inferred_domain: Optional[str] = None
    confidence: Optional[str] = None
    reasoning: Optional[str] = None
    error: Optional[str] = None


class EnterpriseTierResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    enterprise_tier_exists: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class FreeTrialResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    free_trial: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class MinimumSeatsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    minimum_seats: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class MoneyBackResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    money_back_guarantee: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class NumberOfTiersResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    number_of_tiers: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class PlanNamingStyleResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    plan_naming_style: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class PricingModelResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    pricing_model: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class PricingVisibilityResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    pricing_visibility: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class SalesMotionResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    sales_motion: Optional[str] = None
    contact_sales_cta: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class SecurityGatingResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    security_compliance_gating: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class WebinarsRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None


class WebinarsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    has_webinars: Optional[bool] = None
    webinar_count: Optional[int] = None
    webinars: Optional[list] = None
    webinar_topics: Optional[list] = None
    error: Optional[str] = None


class LeadMagicCompanyRequest(BaseModel):
    domain: Optional[str] = None
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    raw_payload: Optional[dict] = None
    workflow_slug: str = "leadmagic-company-enrichment"


class LeadMagicCompanyResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    error: Optional[str] = None


class LinkedInAdsRequest(BaseModel):
    domain: str
    linkedin_ads_payload: dict
    clay_table_url: Optional[str] = None


class LinkedInAdsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    error: Optional[str] = None


class MetaAdsRequest(BaseModel):
    domain: str
    meta_ads_payload: dict
    clay_table_url: Optional[str] = None


class MetaAdsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    platforms: Optional[list] = None
    error: Optional[str] = None


class PredictLeadsTechRequest(BaseModel):
    domain: str
    predictleads_payload: Any
    clay_table_url: Optional[str] = None


class PredictLeadsTechResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    technologies_count: Optional[int] = None
    error: Optional[str] = None


class BuiltWithRequest(BaseModel):
    domain: str
    builtwith_payload: Any
    clay_table_url: Optional[str] = None


class BuiltWithResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    technologies_count: Optional[int] = None
    error: Optional[str] = None


class HasRaisedVCRequest(BaseModel):
    domain: str


class HasRaisedVCResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    has_raised_vc: Optional[bool] = None
    vc_count: Optional[int] = None
    vc_names: Optional[list] = None
    founded_date: Optional[str] = None
    error: Optional[str] = None


class AddOnsOfferedResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    add_ons_offered: Optional[str] = None
    explanation: Optional[str] = None
    error: Optional[str] = None


class CleanedCompanyNameRequest(BaseModel):
    domain: str
    original_company_name: Optional[str] = None
    cleaned_company_name: Optional[str] = None


class CleanedCompanyNameResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    cleaned_company_name: Optional[str] = None
    error: Optional[str] = None


class AnyMailFinderRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    anymailfinder_raw_payload: dict
    workflow_slug: str = "anymailfinder-email"
    clay_table_url: Optional[str] = None


class AnyMailFinderResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    email: Optional[str] = None
    person_mapping_updated: Optional[bool] = None
    error: Optional[str] = None


class IcypeasRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    icypeas_raw_payload: dict
    workflow_slug: str = "icypeas-email"
    clay_table_url: Optional[str] = None


class IcypeasResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    email: Optional[str] = None
    person_mapping_updated: Optional[bool] = None
    error: Optional[str] = None


class LeadMagicEmailRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    leadmagic_raw_payload: dict
    workflow_slug: str = "leadmagic-email"
    clay_table_url: Optional[str] = None


class LeadMagicEmailResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    email: Optional[str] = None
    person_mapping_updated: Optional[bool] = None
    error: Optional[str] = None


class GoogleAdsRequest(BaseModel):
    domain: str
    google_ads_payload: dict
    clay_table_url: Optional[str] = None


class GoogleAdsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    error: Optional[str] = None


class ICPFitCriterionRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None
    raw_target_icp_fit_criterion_payload: dict
    workflow_slug: str = "icp-fit-criterion"


class ICPFitCriterionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    primary_criterion: Optional[str] = None
    criterion_type: Optional[str] = None
    qualifying_signals: Optional[list] = None
    disqualifying_signals: Optional[list] = None
    ideal_company_attributes: Optional[dict] = None
    minimum_requirements: Optional[dict] = None
    error: Optional[str] = None


class ICPIndustriesRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None
    raw_target_icp_industries_payload: dict
    workflow_slug: str = "icp-industries"


class ICPIndustriesResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    raw_industries: Optional[list] = None
    matched_industries: Optional[list] = None
    matched_mapping: Optional[dict] = None
    error: Optional[str] = None


class ICPJobTitlesRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None
    raw_target_icp_job_titles_payload: dict
    workflow_slug: str = "icp-job-titles"


class ICPJobTitlesResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    primary_titles: Optional[list] = None
    influencer_titles: Optional[list] = None
    extended_titles: Optional[list] = None
    error: Optional[str] = None


class ICPValuePropositionRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None
    target_icp_value_prop_payload: dict
    workflow_slug: str = "icp-value-proposition"


class ICPValuePropositionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    value_proposition: Optional[str] = None
    core_benefit: Optional[str] = None
    target_customer: Optional[str] = None
    key_differentiator: Optional[str] = None
    confidence: Optional[str] = None
    error: Optional[str] = None


class ICPVerdictRequest(BaseModel):
    origin_company_domain: str
    company_domain: str
    workflow_slug: str
    label: Optional[str] = None
    verdict: Optional[str] = None
    rationale: Optional[str] = None
    reason: Optional[str] = None
    tokensUsed: Optional[int] = None
    inputTokens: Optional[int] = None
    outputTokens: Optional[int] = None
    totalCostToAIProvider: Optional[str] = None


class ICPVerdictResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    is_match: Optional[bool] = None
    error: Optional[str] = None


class JobPostingRequest(BaseModel):
    domain: str
    job_posting_payload: dict
    clay_table_url: Optional[str] = None


class JobPostingResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    job_id: Optional[int] = None
    raw_payload_id: Optional[str] = None
    title: Optional[str] = None
    normalized_title: Optional[str] = None
    error: Optional[str] = None


class ManualCompanyCustomerRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    company_customer_name: str
    company_customer_domain: Optional[str] = None
    company_customer_linkedin_url: Optional[str] = None
    case_study_url: Optional[str] = None
    has_case_study: Optional[bool] = None
    source_notes: Optional[str] = None
    workflow_slug: str


class ManualCompanyCustomerResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    origin_company_domain: Optional[str] = None
    company_customer_name: Optional[str] = None
    error: Optional[str] = None


class PublicCompanyRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None


class PublicCompanyResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    company_name: Optional[str] = None
    error: Optional[str] = None


class SalesNavCompanyRequest(BaseModel):
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_urn: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    headcount: Optional[str] = None
    industries: Optional[str] = None
    registered_address_raw: Optional[str] = None
    workflow_slug: Optional[str] = "salesnav-company"


class SalesNavCompanyResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    domain: Optional[str] = None
    error: Optional[str] = None


class SalesNavPersonRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    profile_headline: Optional[str] = None
    profile_summary: Optional[str] = None
    job_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_started_on: Optional[str] = None
    person_linkedin_sales_nav_url: Optional[str] = None
    linkedin_user_profile_urn: Optional[str] = None
    location: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source_id: Optional[str] = None
    upload_id: Optional[str] = None
    notes: Optional[str] = None
    matching_filters: Optional[str] = None
    source_created_at: Optional[str] = None
    clay_batch_number: Optional[str] = None
    sent_to_clay_at: Optional[str] = None
    export_title: Optional[str] = None
    export_timestamp: Optional[str] = None
    workflow_slug: Optional[str] = "salesnav-person"


class SalesNavPersonResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    location_matched: Optional[bool] = None
    error: Optional[str] = None


class SignalJobChangeRequest(BaseModel):
    client_domain: str
    raw_job_change_payload: dict
    job_change_within_months: Optional[int] = None
    started_role_within_window: Optional[bool] = None


class SignalJobChangeResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    person_name: Optional[str] = None
    new_company_domain: Optional[str] = None
    error: Optional[str] = None


class SignalJobPostingRequest(BaseModel):
    client_domain: str
    raw_job_post_data_payload: dict
    min_days_since_job_posting: Optional[int] = None
    max_days_since_job_posting: Optional[int] = None


class SignalJobPostingResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    company_domain: Optional[str] = None
    job_title: Optional[str] = None
    error: Optional[str] = None


class SignalPromotionRequest(BaseModel):
    client_domain: str
    raw_promotion_payload: dict
    days_since_promotion: Optional[int] = None


class SignalPromotionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    person_name: Optional[str] = None
    new_title: Optional[str] = None
    error: Optional[str] = None


class VCPortfolioRequest(BaseModel):
    company_name: str
    vc_name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    employee_range: Optional[str] = None
    founded_date: Optional[str] = None
    operating_status: Optional[str] = None
    workflow_slug: Optional[str] = "vc-portfolio"
    clay_table_url: Optional[str] = None


class VCPortfolioResponse(BaseModel):
    success: bool
    raw_payload_id: Optional[str] = None
    extracted_id: Optional[str] = None
    matched_domain: Optional[str] = None
    match_confidence: Optional[str] = None
    linkedin_updated: Optional[bool] = None
    error: Optional[str] = None


class ClaySignalJobChangeRequest(BaseModel):
    person_linkedin_url: str
    job_change_event_raw_payload: Optional[dict] = None
    person_record_raw_payload: Optional[dict] = None
    confidence: Optional[int] = None
    previous_company_linkedin_url: Optional[str] = None
    new_company_linkedin_url: Optional[str] = None
    new_company_domain: Optional[str] = None
    new_company_name: Optional[str] = None
    start_date_at_new_job: Optional[str] = None
    started_within_threshold: Optional[bool] = None
    lookback_threshold_days: Optional[int] = None
    signal_slug: str = "clay-job-change"
    clay_table_url: Optional[str] = None


class ClaySignalJobChangeResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    error: Optional[str] = None


class ClayPersonProfileRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict


class ClayPersonProfileResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    person_profile_id: Optional[str] = None
    experience_count: Optional[int] = None
    education_count: Optional[int] = None
    error: Optional[str] = None


class ClaySignalJobPostingRequest(BaseModel):
    company_linkedin_url: str
    company_record_raw_payload: Optional[Any] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    company_domain: Optional[str] = None
    job_linkedin_url: Optional[str] = None
    post_on: Optional[str] = None
    signal_slug: str = "clay-job-posting"
    clay_table_url: Optional[str] = None


class ClaySignalJobPostingResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    error: Optional[str] = None


class ClaySignalNewHireRequest(BaseModel):
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    signal_slug: str = "clay-new-hire"
    clay_table_url: Optional[str] = None


class ClaySignalNewHireResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    company_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    error: Optional[str] = None


class ClaySignalPromotionRequest(BaseModel):
    person_linkedin_url: str
    promotion_event_raw_payload: Optional[dict] = None
    person_record_raw_payload: Optional[dict] = None
    confidence: Optional[int] = None
    previous_title: Optional[str] = None
    new_title: Optional[str] = None
    start_date_with_new_title: Optional[str] = None
    lookback_threshold_days: Optional[int] = None
    signal_slug: str = "clay-promotion"
    clay_table_url: Optional[str] = None


class ClaySignalPromotionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    error: Optional[str] = None


class CoreCompanySimpleRequest(BaseModel):
    domain: str
    name: Optional[str] = None
    linkedin_url: Optional[str] = None


class CoreCompanySimpleResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    domain: Optional[str] = None
    action: Optional[str] = None
    error: Optional[str] = None


class PersonTitleEnrichmentRequest(BaseModel):
    linkedin_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = False
    has_state: Optional[bool] = False
    has_country: Optional[bool] = False
    company_domain: Optional[str] = None
    latest_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    latest_company: Optional[str] = None
    latest_start_date: Optional[str] = None
    clay_company_table_id: Optional[str] = None
    clay_company_record_id: Optional[str] = None
    seniority_level: Optional[str] = None
    job_function: Optional[str] = None
    workflow_slug: str
    clay_table_url: Optional[str] = None


class PersonTitleEnrichmentResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    error: Optional[str] = None


class BuyerPerson(BaseModel):
    fullName: str
    jobTitle: Optional[str] = ""


class CaseStudyBuyersRequest(BaseModel):
    origin_company_name: str
    origin_company_domain: str
    case_study_url: Optional[str] = ""
    customer_company_name: Optional[str] = ""
    customer_company_domain: Optional[str] = ""
    people: list[BuyerPerson] = []
    success: Optional[bool] = None
    cost_usd: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class CaseStudyBuyersResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    buyer_count: Optional[int] = None
    error: Optional[str] = None


class CaseStudyExtractionRequest(BaseModel):
    origin_company_name: str
    origin_company_domain: str
    case_study_url: str
    company_customer_name: str
    has_case_study_url: bool
    workflow_slug: str


class CaseStudyExtractionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    case_study_id: Optional[str] = None
    champion_count: Optional[int] = None
    customer_domain_found: Optional[bool] = None
    article_title: Optional[str] = None
    error: Optional[str] = None


class CbVcPortfolioRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    short_description: Optional[str] = None
    employee_range: Optional[str] = None
    last_funding_date: Optional[str] = None
    last_funding_type: Optional[str] = None
    last_funding_amount: Optional[str] = None
    last_equity_funding_type: Optional[str] = None
    last_leadership_hiring_date: Optional[str] = None
    founded_date: Optional[str] = None
    estimated_revenue_range: Optional[str] = None
    funding_status: Optional[str] = None
    total_funding_amount: Optional[str] = None
    total_equity_funding_amount: Optional[str] = None
    operating_status: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    vc: Optional[str] = None
    vc1: Optional[str] = None
    vc2: Optional[str] = None
    vc3: Optional[str] = None
    vc4: Optional[str] = None
    vc5: Optional[str] = None
    vc6: Optional[str] = None
    vc7: Optional[str] = None
    vc8: Optional[str] = None
    vc9: Optional[str] = None
    vc10: Optional[str] = None
    vc11: Optional[str] = None
    vc12: Optional[str] = None


class CbVcPortfolioResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    vc_count: Optional[int] = None
    error: Optional[str] = None


class CompanyVCInvestorsRequest(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    vc_og: Optional[str] = None
    vc_1: Optional[str] = None
    vc_2: Optional[str] = None
    vc_3: Optional[str] = None
    vc_4: Optional[str] = None
    vc_5: Optional[str] = None
    vc_6: Optional[str] = None
    vc_7: Optional[str] = None
    vc_8: Optional[str] = None
    vc_9: Optional[str] = None
    vc_10: Optional[str] = None
    vc_11: Optional[str] = None
    vc_12: Optional[str] = None
    workflow_slug: str = "clay-company-vc-investors"


class CompanyVCInvestorsResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    vc_count: Optional[int] = None
    company_name: Optional[str] = None
    error: Optional[str] = None


class CompanyCustomerRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: str
    origin_company_linkedin_url: Optional[str] = None
    workflow_slug: str
    raw_payload: dict


class CompanyCustomerResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    customer_count: Optional[int] = None
    error: Optional[str] = None


class CustomerItem(BaseModel):
    url: Optional[str] = None
    companyName: Optional[str] = None
    hasCaseStudy: Optional[bool] = None


class ClaygentOutput(BaseModel):
    customers: Optional[list[CustomerItem]] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[list[str]] = None


class CompanyCustomersV2Request(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    claygent_output: Optional[ClaygentOutput] = None
    customers_claygent: Optional[ClaygentOutput] = None
    batch_name: Optional[str] = None


class CompanyCustomersV2Response(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    domain: Optional[str] = None
    customers_extracted: Optional[int] = None
    customer_names: Optional[list] = None
    confidence: Optional[str] = None
    error: Optional[str] = None


class CompanyCustomersStructuredRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    response: Optional[str] = None
    customers: Optional[list[CustomerItem]] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[list[str]] = None


class ClaygentOutputResult(BaseModel):
    result: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[list[str]] = None


class CompanyCustomersClaygentRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    claygent_output: Optional[ClaygentOutputResult] = None
    customers_claygent: Optional[ClaygentOutputResult] = None
    batch_name: Optional[str] = None


class CompanyAddressRequest(BaseModel):
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_urn: Optional[str] = None
    domain: Optional[str] = None
    company_description: Optional[str] = None
    company_headcount: Optional[str] = None
    company_industries: Optional[str] = None
    company_registered_address: Optional[str] = None
    workflow_slug: str = "ai-company-address-parsing"


class ParsedAddress(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None


class CompanyAddressResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    parsed_address: Optional[ParsedAddress] = None
    error: Optional[str] = None


class CompanyCustomersLookupRequest(BaseModel):
    domain: str


class CustomerInfo(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    country: Optional[str] = None


class CompanyCustomersLookupResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    customer_count: Optional[int] = None
    customers: Optional[list[CustomerInfo]] = None
    error: Optional[str] = None


class CompanyICPLookupRequest(BaseModel):
    domain: str


class CompanyICPLookupResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    company_name: Optional[str] = None
    customer_domains: Optional[list] = None
    industries: Optional[list] = None
    countries: Optional[list] = None
    employee_ranges: Optional[list] = None
    funding_stages: Optional[list] = None
    job_titles: Optional[list] = None
    seniorities: Optional[list] = None
    job_functions: Optional[list] = None
    value_proposition: Optional[str] = None
    core_benefit: Optional[str] = None
    target_customer: Optional[str] = None
    key_differentiator: Optional[str] = None
    error: Optional[str] = None


class JobTitleLookupRequest(BaseModel):
    job_title: str


class JobTitleLookupResponse(BaseModel):
    match_status: bool
    job_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    job_function: Optional[str] = None
    error: Optional[str] = None


class PersonLocationLookupRequest(BaseModel):
    location_name: str


class PersonLocationLookupResponse(BaseModel):
    match_status: bool
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None
    error: Optional[str] = None


class JobTitleUpdateRequest(BaseModel):
    latest_title: str
    cleaned_job_title: str
    seniority_level: Optional[str] = None
    job_function: Optional[str] = None
    status: Optional[str] = None


class JobTitleUpdateResponse(BaseModel):
    success: bool
    latest_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    seniority_level: Optional[str] = None
    job_function: Optional[str] = None
    error: Optional[str] = None


class LocationUpdateRequest(BaseModel):
    location_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None


class LocationUpdateResponse(BaseModel):
    success: bool
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    error: Optional[str] = None


class CompanyLocationLookupRequest(BaseModel):
    registered_address_raw: str


class CompanyLocationLookupResponse(BaseModel):
    match_status: bool
    registered_address_raw: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None
    error: Optional[str] = None


class SalesnavLocationLookupRequest(BaseModel):
    location_raw: str


class SalesnavLocationLookupResponse(BaseModel):
    match_status: bool
    location_raw: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None
    error: Optional[str] = None


class ProcessSimilarCompaniesQueueRequest(BaseModel):
    batch_size: int = 300
    webhook_url: Optional[str] = None
    similarity_weight: Optional[float] = 0.0
    country_code: Optional[str] = None


class ProcessSimilarCompaniesQueueResponse(BaseModel):
    success: bool
    batch_id: Optional[str] = None
    domains_to_process: Optional[int] = None
    estimated_time_seconds: Optional[float] = None
    webhook_url: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class StagingCompanyLinkedInRequest(BaseModel):
    domain: str
    company_linkedin_url: Optional[str] = None
    short_description: Optional[str] = None


class StagingCompanyLinkedInResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    updated_count: Optional[int] = None
    error: Optional[str] = None


class VCDomainUpdateRequest(BaseModel):
    vc_name: str
    domain: str


class VCDomainUpdateResponse(BaseModel):
    success: bool
    vc_name: Optional[str] = None
    domain: Optional[str] = None
    updated: Optional[int] = None
    error: Optional[str] = None


class CoreCompanyUpsertRequest(BaseModel):
    domain: str
    name: Optional[str] = None
    linkedin_url: Optional[str] = None


class CoreCompanyUpsertResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    domain: Optional[str] = None
    error: Optional[str] = None


class CoreCompanyFullUpsertRequest(BaseModel):
    company_name: str
    domain: str
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    employee_range: Optional[str] = None
    source: str = "gemini-enrichment"


class CoreCompanyFullUpsertResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    company_id: Optional[str] = None
    location_id: Optional[str] = None
    industry_id: Optional[str] = None
    employee_range_id: Optional[str] = None
    linkedin_url_id: Optional[str] = None
    error: Optional[str] = None


class ICPCriteriaUpsertRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None
    industries: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    employee_ranges: Optional[List[str]] = None
    funding_stages: Optional[List[str]] = None
    job_titles: Optional[List[str]] = None
    seniorities: Optional[List[str]] = None
    job_functions: Optional[List[str]] = None
    value_proposition: Optional[str] = None
    core_benefit: Optional[str] = None
    target_customer: Optional[str] = None
    key_differentiator: Optional[str] = None


class ICPCriteriaUpsertResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    id: Optional[str] = None
    error: Optional[str] = None


class BackfillCleanedCompanyNameRequest(BaseModel):
    batch_size: int = 5000
    max_batches: Optional[int] = None


class BackfillCleanedCompanyNameResponse(BaseModel):
    success: bool
    total_updated: Optional[int] = None
    batches_processed: Optional[int] = None
    error: Optional[str] = None


class BackfillCompanyDescriptionsRequest(BaseModel):
    batch_size: int = 1000
    dry_run: bool = False


class BackfillCompanyDescriptionsResponse(BaseModel):
    success: bool
    dry_run: Optional[bool] = None
    updated_count: Optional[int] = None
    source_breakdown: Optional[dict] = None
    error: Optional[str] = None


class BackfillPersonLocationRequest(BaseModel):
    dry_run: bool = True
    limit: Optional[int] = None


class BackfillPersonLocationResponse(BaseModel):
    success: bool = True
    dry_run: Optional[bool] = None
    records_missing_city: Optional[int] = None
    lookup_entries: Optional[int] = None
    matches_in_sample: Optional[int] = None
    sample_size: Optional[int] = None
    sample_matches: Optional[List[dict]] = None
    message: Optional[str] = None
    updated_count: Optional[int] = None
    processed_count: Optional[int] = None
    limit: Optional[int] = None
    errors: Optional[List[dict]] = None
    error_count: Optional[int] = None
    error: Optional[str] = None


class BackfillPersonMatchedLocationRequest(BaseModel):
    dry_run: bool = True
    limit: int = 50000


class BackfillPersonMatchedLocationResponse(BaseModel):
    success: bool = True
    dry_run: Optional[bool] = None
    total_records_to_update: Optional[int] = None
    lookup_entries: Optional[int] = None
    limit: Optional[int] = None
    calls_needed: Optional[int] = None
    records_processed: Optional[int] = None
    updated_count: Optional[int] = None
    skipped_no_match: Optional[int] = None
    errors: Optional[List[dict]] = None
    error_count: Optional[int] = None
    remaining_records: Optional[int] = None
    error: Optional[str] = None


class BackfillPublicCompanyTickerRequest(BaseModel):
    domain: str
    ticker: str


class BackfillPublicCompanyTickerResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    ticker: Optional[str] = None
    error: Optional[str] = None


class CompanyTickerIngestRequest(BaseModel):
    domain: str
    ticker_payload: dict
    clay_table_url: Optional[str] = None


class CompanyTickerIngestResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    ticker: Optional[str] = None
    raw_payload_id: Optional[str] = None
    error: Optional[str] = None


class ClientLeadIngestRequest(BaseModel):
    client_domain: str
    client_form_id: Optional[str] = None
    client_form_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    work_email: Optional[str] = None
    company_domain: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source: Optional[str] = None


class ClientLeadIngestResponse(BaseModel):
    success: bool
    lead_id: Optional[str] = None
    person_id: Optional[str] = None
    company_id: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# Company Endpoints
# =============================================================================

@router.post(
    "/companies/clay-native/firmographics/ingest",
    response_model=CompanyFirmographicsResponse,
    summary="Ingest company firmographics data from Clay",
    description="Wrapper for Modal function: ingest_clay_company_firmo"
)
async def ingest_clay_company_firmo(request: CompanyFirmographicsRequest) -> CompanyFirmographicsResponse:
    """
    Ingest enriched company payload from Clay's company firmographics enrichment.

    Stores raw payload, extracts to company_firmographics table.

    Modal function: ingest_clay_company_firmo
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-company-firmo.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-company-firmo.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyFirmographicsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-native/find-companies/ingest",
    response_model=CompanyDiscoveryResponse,
    summary="Ingest company discovery data from Clay",
    description="Wrapper for Modal function: ingest_clay_find_companies"
)
async def ingest_clay_find_companies(request: CompanyDiscoveryRequest) -> CompanyDiscoveryResponse:
    """
    Ingest company discovery payload from Clay's Find Companies enrichment.

    Stores raw payload, extracts to company_discovery table,
    and maps location/industry against lookup tables.

    Modal function: ingest_clay_find_companies
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-find-companies.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-find-companies.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyDiscoveryResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/type-classification/ingest",
    response_model=CompanyClassificationResponse,
    summary="Ingest company B2B/B2C classification",
    description="Wrapper for Modal function: ingest_company_classification"
)
async def ingest_company_classification(request: CompanyClassificationRequest) -> CompanyClassificationResponse:
    """
    Ingest company classification (B2B/B2C) from Gemini analysis.

    Stores raw payload, extracts to company_classification table,
    and upserts to core.company_business_model.

    Modal function: ingest_company_classification
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-classification.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-company-classification.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyClassificationResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/annual-commitment/infer",
    response_model=AnnualCommitmentResponse,
    summary="Infer if annual commitment is required from pricing page",
    description="Wrapper for Modal function: infer_annual_commitment"
)
async def infer_annual_commitment(request: PricingInferenceRequest) -> AnnualCommitmentResponse:
    """
    Analyze a company's pricing page to determine if annual commitment is required.

    Uses Gemini to classify as: yes, no, or unclear.

    Modal function: infer_annual_commitment
    Modal URL: https://bencrane--hq-master-data-ingest-infer-annual-commitment.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-annual-commitment.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return AnnualCommitmentResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/billing-default/infer",
    response_model=BillingDefaultResponse,
    summary="Infer default billing period from pricing page",
    description="Wrapper for Modal function: infer_billing_default"
)
async def infer_billing_default(request: PricingInferenceRequest) -> BillingDefaultResponse:
    """
    Analyze a company's pricing page to determine default billing period.

    Uses Gemini to classify as: monthly, annual, both_annual_emphasized, both_monthly_emphasized.

    Modal function: infer_billing_default
    Modal URL: https://bencrane--hq-master-data-ingest-infer-billing-default.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-billing-default.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BillingDefaultResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/country/infer",
    response_model=CountryInferenceResponse,
    summary="Infer company headquarters country",
    description="Wrapper for Modal function: infer_company_country"
)
async def infer_company_country(request: CountryInferenceRequest) -> CountryInferenceResponse:
    """
    Infer company headquarters location (city, state, country) using Gemini.

    Modal function: infer_company_country
    Modal URL: https://bencrane--hq-master-data-ingest-infer-company-country.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-company-country.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CountryInferenceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/employee-range/infer",
    response_model=EmployeeRangeInferenceResponse,
    summary="Infer company employee range",
    description="Wrapper for Modal function: infer_company_employee_range"
)
async def infer_company_employee_range(request: EmployeeRangeInferenceRequest) -> EmployeeRangeInferenceResponse:
    """
    Infer company employee range using Gemini.

    Classifies into: 1-10, 11-50, 51-100, 101-250, 251-500, 501-1000, 1001-5000, 5001-10000, 10001+

    Modal function: infer_company_employee_range
    Modal URL: https://bencrane--hq-master-data-ingest-infer-company-employee-range.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-company-employee-range.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return EmployeeRangeInferenceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/industry/infer",
    response_model=IndustryInferenceResponse,
    summary="Infer company industry",
    description="Wrapper for Modal function: infer_company_industry"
)
async def infer_company_industry(request: IndustryInferenceRequest) -> IndustryInferenceResponse:
    """
    Infer company industry using Gemini, then fuzzy match against reference industries.

    Modal function: infer_company_industry
    Modal URL: https://bencrane--hq-master-data-ingest-infer-company-industry.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-company-industry.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return IndustryInferenceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/linkedin-url/get",
    response_model=LinkedInUrlInferenceResponse,
    summary="Infer company LinkedIn URL",
    description="Wrapper for Modal function: infer_company_linkedin_url"
)
async def infer_company_linkedin_url(request: LinkedInUrlInferenceRequest) -> LinkedInUrlInferenceResponse:
    """
    Infer company LinkedIn URL using Gemini.

    Modal function: infer_company_linkedin_url
    Modal URL: https://bencrane--hq-master-data-ingest-infer-company-linkedin-url.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-company-linkedin-url.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return LinkedInUrlInferenceResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/comparison-page-check/infer",
    response_model=ComparisonPageResponse,
    summary="Check if company has a comparison page",
    description="Wrapper for Modal function: infer_comparison_page_exists"
)
async def infer_comparison_page_exists(request: ComparisonPageRequest) -> ComparisonPageResponse:
    """
    Analyze if a company has a comparison page on their website.

    Uses Gemini to determine if a comparison/alternative page exists.

    Modal function: infer_comparison_page_exists
    Modal URL: https://bencrane--hq-master-data-ingest-infer-comparison-page-exists.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-comparison-page-exists.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ComparisonPageResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/crunchbase-url/get",
    response_model=CrunchbaseUrlResponse,
    summary="Infer company domain from Crunchbase URL",
    description="Wrapper for Modal function: infer_crunchbase_domain"
)
async def infer_crunchbase_domain(request: CrunchbaseUrlRequest) -> CrunchbaseUrlResponse:
    """
    Infer company domain from Crunchbase data using Gemini.

    Takes a company name and Crunchbase URL, returns the inferred website domain.

    Modal function: infer_crunchbase_domain
    Modal URL: https://bencrane--hq-master-data-ingest-infer-crunchbase-domain.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-crunchbase-domain.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CrunchbaseUrlResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/enterprise-tier-check/infer",
    response_model=EnterpriseTierResponse,
    summary="Check if company has an enterprise pricing tier",
    description="Wrapper for Modal function: infer_enterprise_tier_exists"
)
async def infer_enterprise_tier_exists(request: PricingInferenceRequest) -> EnterpriseTierResponse:
    """
    Analyze a company's pricing page to determine if an enterprise tier exists.

    Uses Gemini to classify as: yes or no.

    Modal function: infer_enterprise_tier_exists
    Modal URL: https://bencrane--hq-master-data-ingest-infer-enterprise-tier-exists.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-enterprise-tier-exists.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return EnterpriseTierResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/free-trial-check/infer",
    response_model=FreeTrialResponse,
    summary="Check if company offers a free trial",
    description="Wrapper for Modal function: infer_free_trial"
)
async def infer_free_trial(request: PricingInferenceRequest) -> FreeTrialResponse:
    """
    Analyze a company's pricing page to determine if a free trial is offered.

    Uses Gemini to classify as: yes, no, or demo_only.

    Modal function: infer_free_trial
    Modal URL: https://bencrane--hq-master-data-ingest-infer-free-trial.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-free-trial.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return FreeTrialResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/min-seats-check/infer",
    response_model=MinimumSeatsResponse,
    summary="Check if company requires minimum seats",
    description="Wrapper for Modal function: infer_minimum_seats"
)
async def infer_minimum_seats(request: PricingInferenceRequest) -> MinimumSeatsResponse:
    """
    Analyze a company's pricing page to determine if minimum seats are required.

    Uses Gemini to classify as: yes, no, or not_mentioned.

    Modal function: infer_minimum_seats
    Modal URL: https://bencrane--hq-master-data-ingest-infer-minimum-seats.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-minimum-seats.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return MinimumSeatsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/money-back-check/infer",
    response_model=MoneyBackResponse,
    summary="Check if company offers money back guarantee",
    description="Wrapper for Modal function: infer_money_back_guarantee"
)
async def infer_money_back_guarantee(request: PricingInferenceRequest) -> MoneyBackResponse:
    """
    Analyze a company's pricing page to determine if a money back guarantee is offered.

    Uses Gemini to classify as: yes or no.

    Modal function: infer_money_back_guarantee
    Modal URL: https://bencrane--hq-master-data-ingest-infer-money-back-guarantee.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-money-back-guarantee.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return MoneyBackResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/tier-number-check/infer",
    response_model=NumberOfTiersResponse,
    summary="Count number of pricing tiers",
    description="Wrapper for Modal function: infer_number_of_tiers"
)
async def infer_number_of_tiers(request: PricingInferenceRequest) -> NumberOfTiersResponse:
    """
    Analyze a company's pricing page to count pricing tiers.

    Uses Gemini to classify as: 1, 2, 3, or 4+.

    Modal function: infer_number_of_tiers
    Modal URL: https://bencrane--hq-master-data-ingest-infer-number-of-tiers.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-number-of-tiers.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return NumberOfTiersResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/plan-naming-check/infer",
    response_model=PlanNamingStyleResponse,
    summary="Determine plan naming style",
    description="Wrapper for Modal function: infer_plan_naming_style"
)
async def infer_plan_naming_style(request: PricingInferenceRequest) -> PlanNamingStyleResponse:
    """
    Analyze a company's pricing page to determine plan naming style.

    Uses Gemini to classify as: generic, persona_based, feature_based, or other.

    Modal function: infer_plan_naming_style
    Modal URL: https://bencrane--hq-master-data-ingest-infer-plan-naming-style.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-plan-naming-style.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PlanNamingStyleResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/pricing-model-check/infer",
    response_model=PricingModelResponse,
    summary="Determine pricing model type",
    description="Wrapper for Modal function: infer_pricing_model"
)
async def infer_pricing_model(request: PricingInferenceRequest) -> PricingModelResponse:
    """
    Analyze a company's pricing page to determine pricing model.

    Uses Gemini to classify as: seat_based, usage_based, flat, tiered, custom, or multiple.

    Modal function: infer_pricing_model
    Modal URL: https://bencrane--hq-master-data-ingest-infer-pricing-model.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-pricing-model.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PricingModelResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/pricing-visibility-check/infer",
    response_model=PricingVisibilityResponse,
    summary="Determine pricing visibility",
    description="Wrapper for Modal function: infer_pricing_visibility"
)
async def infer_pricing_visibility(request: PricingInferenceRequest) -> PricingVisibilityResponse:
    """
    Analyze a company's pricing page to determine pricing visibility.

    Uses Gemini to classify as: public, hidden, or partial.

    Modal function: infer_pricing_visibility
    Modal URL: https://bencrane--hq-master-data-ingest-infer-pricing-visibility.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-pricing-visibility.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PricingVisibilityResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/sales-motion-check/infer",
    response_model=SalesMotionResponse,
    summary="Classify company sales motion",
    description="Wrapper for Modal function: infer_sales_motion"
)
async def infer_sales_motion(request: PricingInferenceRequest) -> SalesMotionResponse:
    """
    Analyze a company's pricing page to classify their sales motion.

    Uses Gemini to classify as: self_serve, sales_led, or hybrid.
    Also detects if a Contact Sales CTA is present.

    Modal function: infer_sales_motion
    Modal URL: https://bencrane--hq-master-data-ingest-infer-sales-motion.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-sales-motion.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SalesMotionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/security-gating-check/infer",
    response_model=SecurityGatingResponse,
    summary="Check if security features are gated to higher tiers",
    description="Wrapper for Modal function: infer_security_gating"
)
async def infer_security_gating(request: PricingInferenceRequest) -> SecurityGatingResponse:
    """
    Analyze a company's pricing page to determine if security/compliance features are gated.

    Uses Gemini to classify as: yes, no, or not_mentioned.

    Modal function: infer_security_gating
    Modal URL: https://bencrane--hq-master-data-ingest-infer-security-gating.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-security-gating.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SecurityGatingResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/webinars-status-data/infer",
    response_model=WebinarsResponse,
    summary="Extract webinar data from company website",
    description="Wrapper for Modal function: infer_webinars"
)
async def infer_webinars(request: WebinarsRequest) -> WebinarsResponse:
    """
    Analyze a company's website to extract webinar information.

    Finds webinar page, extracts individual webinars with titles and topics.

    Modal function: infer_webinars
    Modal URL: https://bencrane--hq-master-data-ingest-infer-webinars.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-webinars.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return WebinarsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-leadmagic/enrich/ingest",
    response_model=LeadMagicCompanyResponse,
    summary="Ingest LeadMagic company enrichment data",
    description="Wrapper for Modal function: ingest_leadmagic_company"
)
async def ingest_leadmagic_company(request: LeadMagicCompanyRequest) -> LeadMagicCompanyResponse:
    """
    Ingest company enrichment data from LeadMagic.

    Stores raw payload, extracts key fields to extracted table.

    Modal function: ingest_leadmagic_company
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-leadmagic-company.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-leadmagic-company.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return LeadMagicCompanyResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-adyntel/linkedin-ads/ingest",
    response_model=LinkedInAdsResponse,
    summary="Ingest LinkedIn ads data from Adyntel",
    description="Wrapper for Modal function: ingest_linkedin_ads"
)
async def ingest_linkedin_ads(request: LinkedInAdsRequest) -> LinkedInAdsResponse:
    """
    Ingest LinkedIn advertising data from Adyntel.

    Stores raw payload, extracts individual ads, updates core summary.

    Modal function: ingest_linkedin_ads
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-linkedin-ads.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-linkedin-ads.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return LinkedInAdsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-adyntel/meta-ads/ingest",
    response_model=MetaAdsResponse,
    summary="Ingest Meta/Facebook ads data from Adyntel",
    description="Wrapper for Modal function: ingest_meta_ads"
)
async def ingest_meta_ads(request: MetaAdsRequest) -> MetaAdsResponse:
    """
    Ingest Meta (Facebook/Instagram) advertising data from Adyntel.

    Stores raw payload, extracts individual ads, updates core summary.

    Modal function: ingest_meta_ads
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-meta-ads.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-meta-ads.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return MetaAdsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-adyntel/google-ads/ingest",
    response_model=GoogleAdsResponse,
    summary="Ingest Google ads data from Adyntel",
    description="Wrapper for Modal function: ingest_google_ads"
)
async def ingest_google_ads(request: GoogleAdsRequest) -> GoogleAdsResponse:
    """
    Ingest Google advertising data from Adyntel.

    Stores raw payload, extracts individual ads, updates core summary.

    Modal function: ingest_google_ads
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-google-ads.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-google-ads.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return GoogleAdsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-predictleads/get-tech-stack/ingest",
    response_model=PredictLeadsTechResponse,
    summary="Ingest PredictLeads tech stack data",
    description="Wrapper for Modal function: ingest_predictleads_techstack"
)
async def ingest_predictleads_techstack(request: PredictLeadsTechRequest) -> PredictLeadsTechResponse:
    """
    Ingest technology stack data from PredictLeads.

    Stores raw payload, extracts technologies to extracted and core tables.

    Modal function: ingest_predictleads_techstack
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-predictleads-techstack.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-predictleads-techstack.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PredictLeadsTechResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/built-with/site-tech/ingest",
    response_model=BuiltWithResponse,
    summary="Ingest BuiltWith tech stack data",
    description="Wrapper for Modal function: ingest_builtwith"
)
async def ingest_builtwith(request: BuiltWithRequest) -> BuiltWithResponse:
    """
    Ingest technology stack data from BuiltWith.

    Stores raw payload, extracts technologies to extracted, reference, and core tables.

    Modal function: ingest_builtwith
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-builtwith.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-builtwith.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BuiltWithResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/has-raised-vc-status/check",
    response_model=HasRaisedVCResponse,
    summary="Check if company has raised VC funding",
    description="Wrapper for Modal function: has_raised_vc"
)
async def has_raised_vc(request: HasRaisedVCRequest) -> HasRaisedVCResponse:
    """
    Check if a company has raised VC funding.

    Looks up the domain in extracted.vc_portfolio and returns VC details if found.

    Modal function: has_raised_vc
    Modal URL: https://bencrane--hq-master-data-ingest-has-raised-vc.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-has-raised-vc.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return HasRaisedVCResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/add-ons-offered/infer",
    response_model=AddOnsOfferedResponse,
    summary="Check if company offers add-ons",
    description="Wrapper for Modal function: infer_add_ons_offered"
)
async def infer_add_ons_offered(request: PricingInferenceRequest) -> AddOnsOfferedResponse:
    """
    Analyze a company's pricing page to determine if add-ons are offered.

    Uses Gemini to classify as: yes, no, or unclear.

    Modal function: infer_add_ons_offered
    Modal URL: https://bencrane--hq-master-data-ingest-infer-add-ons-offered.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-infer-add-ons-offered.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return AddOnsOfferedResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-native/normalize-company/ingest",
    response_model=CleanedCompanyNameResponse,
    summary="Ingest cleaned/normalized company name",
    description="Wrapper for Modal function: ingest_cleaned_company_name"
)
async def ingest_cleaned_company_name(request: CleanedCompanyNameRequest) -> CleanedCompanyNameResponse:
    """
    Ingest a cleaned company name from Clay.

    Stores the canonical cleaned name to avoid messy names like "WUNDERGROUND LLC".

    Modal function: ingest_cleaned_company_name
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-cleaned-company-name.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-cleaned-company-name.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CleanedCompanyNameResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-fit-criterion/ingest",
    response_model=ICPFitCriterionResponse,
    summary="Ingest ICP fit criterion analysis",
    description="Wrapper for Modal function: ingest_icp_fit_criterion"
)
async def ingest_icp_fit_criterion(request: ICPFitCriterionRequest) -> ICPFitCriterionResponse:
    """
    Ingest ICP fit criterion analysis for a company.

    Stores raw payload and extracts qualifying/disqualifying signals,
    ideal company attributes, and minimum requirements.

    Modal function: ingest_icp_fit_criterion
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-icp-fit-criterion.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-icp-fit-criterion.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPFitCriterionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-industries/ingest",
    response_model=ICPIndustriesResponse,
    summary="Ingest ICP target industries",
    description="Wrapper for Modal function: ingest_icp_industries"
)
async def ingest_icp_industries(request: ICPIndustriesRequest) -> ICPIndustriesResponse:
    """
    Ingest ICP target industries for a company.

    Stores raw payload, extracts industries and matches to canonical industries using GPT.

    Modal function: ingest_icp_industries
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-icp-industries.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-icp-industries.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPIndustriesResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-job-titles/ingest",
    response_model=ICPJobTitlesResponse,
    summary="Ingest ICP target job titles",
    description="Wrapper for Modal function: ingest_icp_job_titles"
)
async def ingest_icp_job_titles(request: ICPJobTitlesRequest) -> ICPJobTitlesResponse:
    """
    Ingest ICP target job titles for a company.

    Stores raw payload, extracts and normalizes job titles (camelCase -> human-readable).

    Modal function: ingest_icp_job_titles
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-icp-job-titles.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-icp-job-titles.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPJobTitlesResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-value-prop/ingest",
    response_model=ICPValuePropositionResponse,
    summary="Ingest ICP value proposition",
    description="Wrapper for Modal function: ingest_icp_value_proposition"
)
async def ingest_icp_value_proposition(request: ICPValuePropositionRequest) -> ICPValuePropositionResponse:
    """
    Ingest ICP value proposition for a company.

    Stores raw payload and extracts value proposition, core benefit, target customer, key differentiator.

    Modal function: ingest_icp_value_proposition
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-icp-value-proposition.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-icp-value-proposition.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPValuePropositionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-verdict/ingest",
    response_model=ICPVerdictResponse,
    summary="Ingest ICP verdict",
    description="Wrapper for Modal function: ingest_icp_verdict"
)
async def ingest_icp_verdict(request: ICPVerdictRequest) -> ICPVerdictResponse:
    """
    Ingest ICP verdict payload from Clay.

    Stores raw payload and extracts normalized verdict data.

    Modal function: ingest_icp_verdict
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-icp-verdict.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-icp-verdict.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPVerdictResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/icp-job-posting/ingest",
    response_model=JobPostingResponse,
    summary="Ingest job posting data",
    description="Wrapper for Modal function: ingest_job_posting"
)
async def ingest_job_posting(request: JobPostingRequest) -> JobPostingResponse:
    """
    Ingest job posting data for a company.

    Stores raw payload, extracts to extracted.company_job_postings,
    upserts to reference.job_titles, and core.company_job_postings.

    Modal function: ingest_job_posting
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-job-posting.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-job-posting.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return JobPostingResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/manual/customers/ingest",
    response_model=ManualCompanyCustomerResponse,
    summary="Ingest manual company customer data",
    description="Wrapper for Modal function: ingest_manual_comp_customer"
)
async def ingest_manual_comp_customer(request: ManualCompanyCustomerRequest) -> ManualCompanyCustomerResponse:
    """
    Ingest manually-sourced company customer data.

    Data is already flattened, upserts directly to raw.manual_company_customers.

    Modal function: ingest_manual_comp_customer
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-manual-comp-customer.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-manual-comp-customer.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ManualCompanyCustomerResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/manual/public-company-check/ingest",
    response_model=PublicCompanyResponse,
    summary="Ingest public company data",
    description="Wrapper for Modal function: ingest_public_company"
)
async def ingest_public_company(request: PublicCompanyRequest) -> PublicCompanyResponse:
    """
    Add a known public company to core.company_public.

    Modal function: ingest_public_company
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-public-company.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-public-company.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PublicCompanyResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/manual/core-data/ingest",
    response_model=CoreCompanySimpleResponse,
    summary="Upsert company to core.companies",
    description="Wrapper for Modal function: ingest_core_company_simple"
)
async def ingest_core_company_simple(request: CoreCompanySimpleRequest) -> CoreCompanySimpleResponse:
    """
    Upsert company data directly to core.companies.

    If domain exists, updates name and linkedin_url.
    If domain doesn't exist, inserts new record.

    Modal function: ingest_core_company_simple
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-core-company-simple.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-core-company-simple.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CoreCompanySimpleResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/not-sure/case-study-buyers/ingest",
    response_model=CaseStudyBuyersResponse,
    summary="Ingest case study buyers data",
    description="Wrapper for Modal function: ingest_case_study_buyers"
)
async def ingest_case_study_buyers(request: CaseStudyBuyersRequest) -> CaseStudyBuyersResponse:
    """
    Ingest case study buyers payload.

    Stores raw payload, then extracts each person to flattened table.

    Modal function: ingest_case_study_buyers
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-case-study-buyers.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-case-study-buyers.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CaseStudyBuyersResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/gemini/case-study-extraction/ingest",
    response_model=CaseStudyExtractionResponse,
    summary="Extract case study details using Gemini",
    description="Wrapper for Modal function: ingest_case_study_extraction"
)
async def ingest_case_study_extraction(request: CaseStudyExtractionRequest) -> CaseStudyExtractionResponse:
    """
    Extract case study details using Gemini Flash.

    Stores raw Gemini response, then extracts to case_study_details and case_study_champions.

    Modal function: ingest_case_study_extraction
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-case-study-extraction.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-case-study-extraction.modal.run"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CaseStudyExtractionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/salesnav/scraped-data/ingest",
    response_model=SalesNavCompanyResponse,
    summary="Ingest SalesNav company data",
    description="Wrapper for Modal function: ingest_salesnav_company"
)
async def ingest_salesnav_company(request: SalesNavCompanyRequest) -> SalesNavCompanyResponse:
    """
    Ingest SalesNav company data.

    Stores raw payload, then extracts to salesnav_scrapes_companies.

    Modal function: ingest_salesnav_company
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-salesnav-company.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-salesnav-company.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SalesNavCompanyResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/cb/vc-portfolio/ingest",
    response_model=CbVcPortfolioResponse,
    summary="Ingest CB VC portfolio company data",
    description="Wrapper for Modal function: ingest_cb_vc_portfolio"
)
async def ingest_cb_vc_portfolio(request: CbVcPortfolioRequest) -> CbVcPortfolioResponse:
    """
    Ingest CB VC portfolio data.

    Stores raw payload, then extracts one row per VC to extracted table.

    Modal function: ingest_cb_vc_portfolio
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-cb-vc-portfolio.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-cb-vc-portfolio.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CbVcPortfolioResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/cb/company-investors/ingest",
    response_model=CompanyVCInvestorsResponse,
    summary="Ingest company VC investors data",
    description="Wrapper for Modal function: ingest_company_vc_investors"
)
async def ingest_company_vc_investors(request: CompanyVCInvestorsRequest) -> CompanyVCInvestorsResponse:
    """
    Ingest company VC investor data.

    Receives a company with up to 12 VC co-investors and explodes them into normalized rows.

    Modal function: ingest_company_vc_investors
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-vc-investors.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-company-vc-investors.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyVCInvestorsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/claygent/customers-of-1/ingest",
    response_model=CompanyCustomerResponse,
    summary="Ingest company customers (variant 1)",
    description="Wrapper for Modal function: ingest_all_comp_customers"
)
async def ingest_all_comp_customers(request: CompanyCustomerRequest) -> CompanyCustomerResponse:
    """
    Ingest customer research payload from Claygent.

    Stores raw payload, then extracts company customers to individual rows.

    Modal function: ingest_all_comp_customers
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-all-comp-customers.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-all-comp-customers.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyCustomerResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/claygent/customers-of-2/ingest",
    response_model=CompanyCustomersV2Response,
    summary="Ingest company customers (variant 2)",
    description="Wrapper for Modal function: ingest_company_customers_v2"
)
async def ingest_company_customers_v2(request: CompanyCustomersV2Request) -> CompanyCustomersV2Response:
    """
    Ingest structured customers output from Clay webhook.

    Handles empty customers arrays - stores raw, extracts 0 customers.

    Modal function: ingest_company_customers_v2
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-customers-v2.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-company-customers-v2.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyCustomersV2Response(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/claygent/customers-of-3/ingest",
    response_model=CompanyCustomersV2Response,
    summary="Ingest company customers (variant 3 - structured)",
    description="Wrapper for Modal function: ingest_company_customers_structured"
)
async def ingest_company_customers_structured(request: CompanyCustomersStructuredRequest) -> CompanyCustomersV2Response:
    """
    Ingest structured customers output with flat payload structure.

    Modal function: ingest_company_customers_structured
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-customers-85468a.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-ingest-company-customers-85468a.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyCustomersV2Response(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/claygent/customers-of-4/ingest",
    response_model=CompanyCustomersV2Response,
    summary="Ingest company customers (variant 4 - claygent)",
    description="Wrapper for Modal function: ingest_company_customers_claygent"
)
async def ingest_company_customers_claygent(request: CompanyCustomersClaygentRequest) -> CompanyCustomersV2Response:
    """
    Ingest Claygent customers output from Clay webhook.

    Parses comma-separated customer names from result field.

    Modal function: ingest_company_customers_claygent
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-customers-a12938.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-ingest-company-customers-a12938.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyCustomersV2Response(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/claygent/company-address-parsing/ingest",
    response_model=CompanyAddressResponse,
    summary="Parse company address with AI",
    description="Wrapper for Modal function: ingest_company_address_parsing"
)
async def ingest_company_address_parsing(request: CompanyAddressRequest) -> CompanyAddressResponse:
    """
    Ingest company record, parse address with Gemini, store raw + extracted.

    Modal function: ingest_company_address_parsing
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-address-parsing.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-company-address-parsing.modal.run"

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyAddressResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/company-customers/lookup",
    response_model=CompanyCustomersLookupResponse,
    summary="Lookup company customers by domain",
    description="Wrapper for Modal function: lookup_company_customers"
)
async def lookup_company_customers(request: CompanyCustomersLookupRequest) -> CompanyCustomersLookupResponse:
    """
    Lookup customer companies for a given domain from core tables.

    Modal function: lookup_company_customers
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-company-customers.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-company-customers.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyCustomersLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/company-icp/lookup",
    response_model=CompanyICPLookupResponse,
    summary="Lookup company ICP criteria by domain",
    description="Wrapper for Modal function: lookup_company_icp"
)
async def lookup_company_icp(request: CompanyICPLookupRequest) -> CompanyICPLookupResponse:
    """
    Lookup company ICP data by domain.

    Checks core.icp_criteria first, falls back to extracted tables.

    Modal function: lookup_company_icp
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-company-icp.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-company-icp.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyICPLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/clay-native/signal-job-posting-2/ingest",
    response_model=ClaySignalJobPostingResponse,
    summary="Ingest Clay job posting signal data",
    description="Wrapper for Modal function: ingest_clay_signal_job_posting"
)
async def ingest_clay_signal_job_posting(request: ClaySignalJobPostingRequest) -> ClaySignalJobPostingResponse:
    """
    Ingest Clay "Job Posting" signal payload.

    Stores raw payload, then extracts to extracted.clay_job_posting table.

    Modal function: ingest_clay_signal_job_posting
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-posting.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-signal-job-posting.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClaySignalJobPostingResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


# =============================================================================
# People Endpoints
# =============================================================================

@router.post(
    "/people/db/person-job-title/lookup",
    response_model=JobTitleLookupResponse,
    summary="Lookup job title in reference table",
    description="Wrapper for Modal function: lookup_job_title"
)
async def lookup_job_title(request: JobTitleLookupRequest) -> JobTitleLookupResponse:
    """
    Check if job_title exists in reference.job_title_lookup.

    Returns cleaned_job_title, seniority_level, job_function if found.

    Modal function: lookup_job_title
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-job-title.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-job-title.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return JobTitleLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/db/person-location/lookup",
    response_model=PersonLocationLookupResponse,
    summary="Lookup person location in reference table",
    description="Wrapper for Modal function: lookup_person_location"
)
async def lookup_person_location(request: PersonLocationLookupRequest) -> PersonLocationLookupResponse:
    """
    Check if location_name exists in reference.location_lookup.

    Returns city, state, country if found.

    Modal function: lookup_person_location
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-person-location.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-person-location.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PersonLocationLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/find-people/ingest",
    response_model=PersonIngestResponse,
    summary="Ingest person discovery data from Clay",
    description="Wrapper for Modal function: ingest_clay_find_people"
)
async def ingest_clay_find_people(request: PersonDiscoveryRequest) -> PersonIngestResponse:
    """
    Ingest person discovery payload from Clay's Find People enrichment.

    Stores raw payload, extracts to person_discovery table,
    and maps location/job title against lookup tables.

    Modal function: ingest_clay_find_people
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-find-people.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-find-people.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PersonIngestResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-anymail/get-email/ingest",
    response_model=AnyMailFinderResponse,
    summary="Ingest AnyMailFinder email lookup results",
    description="Wrapper for Modal function: ingest_email_anymailfinder"
)
async def ingest_email_anymailfinder(request: AnyMailFinderRequest) -> AnyMailFinderResponse:
    """
    Ingest email lookup results from AnyMailFinder.

    Stores raw payload, extracts to normalized table, updates reference mappings.

    Modal function: ingest_email_anymailfinder
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-email-anymailfinder.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-email-anymailfinder.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return AnyMailFinderResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-icypeas/get-email/ingest",
    response_model=IcypeasResponse,
    summary="Ingest Icypeas email lookup results",
    description="Wrapper for Modal function: ingest_email_icypeas"
)
async def ingest_email_icypeas(request: IcypeasRequest) -> IcypeasResponse:
    """
    Ingest email lookup results from Icypeas.

    Stores raw payload, extracts to normalized table, updates reference mappings.

    Modal function: ingest_email_icypeas
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-email-icypeas.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-email-icypeas.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return IcypeasResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-leadmagic/get-email/ingest",
    response_model=LeadMagicEmailResponse,
    summary="Ingest LeadMagic email lookup results",
    description="Wrapper for Modal function: ingest_email_leadmagic"
)
async def ingest_email_leadmagic(request: LeadMagicEmailRequest) -> LeadMagicEmailResponse:
    """
    Ingest email lookup results from LeadMagic.

    Stores raw payload, extracts to normalized table, updates reference mappings.

    Modal function: ingest_email_leadmagic
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-email-leadmagic.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-email-leadmagic.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return LeadMagicEmailResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/salesnav/scraped-data/ingest",
    response_model=SalesNavPersonResponse,
    summary="Ingest SalesNav person data",
    description="Wrapper for Modal function: ingest_salesnav_person"
)
async def ingest_salesnav_person(request: SalesNavPersonRequest) -> SalesNavPersonResponse:
    """
    Ingest person data from SalesNav scrapes.

    Location is matched against reference.salesnav_location_lookup table.

    Modal function: ingest_salesnav_person
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-salesnav-person.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-salesnav-person.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SalesNavPersonResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-job-change/ingest",
    response_model=SignalJobChangeResponse,
    summary="Ingest job change signal data",
    description="Wrapper for Modal function: ingest_signal_job_change"
)
async def ingest_signal_job_change(request: SignalJobChangeRequest) -> SignalJobChangeResponse:
    """
    Ingest job change signal payload.

    Stores raw payload, then extracts to extracted.signal_job_change table.

    Modal function: ingest_signal_job_change
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-signal-job-change.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-signal-job-change.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SignalJobChangeResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-job-posting/ingest",
    response_model=SignalJobPostingResponse,
    summary="Ingest job posting signal data",
    description="Wrapper for Modal function: ingest_signal_job_posting"
)
async def ingest_signal_job_posting(request: SignalJobPostingRequest) -> SignalJobPostingResponse:
    """
    Ingest job posting signal payload.

    Stores raw payload, then extracts to extracted.signal_job_posting table.

    Modal function: ingest_signal_job_posting
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-signal-job-posting.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-signal-job-posting.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SignalJobPostingResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-promotion/ingest",
    response_model=SignalPromotionResponse,
    summary="Ingest promotion signal data",
    description="Wrapper for Modal function: ingest_signal_promotion"
)
async def ingest_signal_promotion(request: SignalPromotionRequest) -> SignalPromotionResponse:
    """
    Ingest promotion signal payload.

    Stores raw payload, then extracts to extracted.signal_promotion table.

    Modal function: ingest_signal_promotion
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-signal-promotion.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-signal-promotion.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SignalPromotionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-job-change-2/ingest",
    response_model=ClaySignalJobChangeResponse,
    summary="Ingest Clay job change signal data",
    description="Wrapper for Modal function: ingest_clay_signal_job_change"
)
async def ingest_clay_signal_job_change(request: ClaySignalJobChangeRequest) -> ClaySignalJobChangeResponse:
    """
    Ingest Clay "Job Change" signal payload.

    Stores raw payload, then extracts to extracted.clay_job_change table.

    Modal function: ingest_clay_signal_job_change
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-signal-job-change.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-signal-job-change.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClaySignalJobChangeResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/person-profile/ingest",
    response_model=ClayPersonProfileResponse,
    summary="Ingest Clay person profile data",
    description="Wrapper for Modal function: ingest_clay_person_profile"
)
async def ingest_clay_person_profile(request: ClayPersonProfileRequest) -> ClayPersonProfileResponse:
    """
    Ingest enriched person payload from Clay.

    Stores raw payload, then extracts to person_profile, person_experience, person_education.

    Modal function: ingest_clay_person_profile
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-person-profile.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-person-profile.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClayPersonProfileResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-new-hire-2/ingest",
    response_model=ClaySignalNewHireResponse,
    summary="Ingest Clay new hire signal data",
    description="Wrapper for Modal function: ingest_clay_signal_new_hire"
)
async def ingest_clay_signal_new_hire(request: ClaySignalNewHireRequest) -> ClaySignalNewHireResponse:
    """
    Ingest Clay "New Hire" signal payload.

    Stores raw payload, then extracts to extracted.clay_new_hire table.

    Modal function: ingest_clay_signal_new_hire
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-signal-new-hire.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-signal-new-hire.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClaySignalNewHireResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/clay-native/signal-promotion-2/ingest",
    response_model=ClaySignalPromotionResponse,
    summary="Ingest Clay promotion signal data",
    description="Wrapper for Modal function: ingest_clay_signal_promotion"
)
async def ingest_clay_signal_promotion(request: ClaySignalPromotionRequest) -> ClaySignalPromotionResponse:
    """
    Ingest Clay "Promotion" signal payload.

    Stores raw payload, then extracts to extracted.clay_promotion table.

    Modal function: ingest_clay_signal_promotion
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-clay-signal-promotion.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-clay-signal-promotion.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClaySignalPromotionResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/not-sure/job-title-clean/ingest",
    response_model=PersonTitleEnrichmentResponse,
    summary="Ingest person title enrichment data",
    description="Wrapper for Modal function: ingest_ppl_title_enrich"
)
async def ingest_ppl_title_enrich(request: PersonTitleEnrichmentRequest) -> PersonTitleEnrichmentResponse:
    """
    Ingest person data with title enrichment (seniority_level, job_function, cleaned_job_title).

    Stores raw payload, then extracts to person_title_enrichment table.

    Modal function: ingest_ppl_title_enrich
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-ppl-title-enrich.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-ppl-title-enrich.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return PersonTitleEnrichmentResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/salesnav-company-location/lookup",
    response_model=CompanyLocationLookupResponse,
    summary="Lookup company location from SalesNav registered address",
    description="Wrapper for Modal function: lookup_salesnav_company_location"
)
async def lookup_salesnav_company_location(request: CompanyLocationLookupRequest) -> CompanyLocationLookupResponse:
    """
    Check if registered_address_raw exists in reference.salesnav_company_location_lookup.

    Returns match_status=True with city/state/country if found, False otherwise.

    Modal function: lookup_salesnav_company_location
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-salesnav-company--1838bd.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-lookup-salesnav-company--1838bd.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyLocationLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/--/db/salesnav-person/lookup",
    response_model=SalesnavLocationLookupResponse,
    summary="Lookup person location from SalesNav location string",
    description="Wrapper for Modal function: lookup_salesnav_location"
)
async def lookup_salesnav_location(request: SalesnavLocationLookupRequest) -> SalesnavLocationLookupResponse:
    """
    Check if location_raw exists in reference.salesnav_location_lookup.

    Returns match_status=True with city/state/country if found, False otherwise.

    Modal function: lookup_salesnav_location
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-salesnav-location.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-salesnav-location.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SalesnavLocationLookupResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/IGNORE/IGNORE/IGNORE/process",
    response_model=ProcessSimilarCompaniesQueueResponse,
    summary="Process similar companies queue",
    description="Wrapper for Modal function: process_similar_companies_queue"
)
async def process_similar_companies_queue(request: ProcessSimilarCompaniesQueueRequest) -> ProcessSimilarCompaniesQueueResponse:
    """
    Process next N domains from the similar companies queue.

    Returns immediately with batch_id. Spawns background worker to process.
    Calls webhook_url when done (if provided).

    Modal function: process_similar_companies_queue
    Modal URL: https://bencrane--hq-master-data-ingest-process-similar-companies-queue.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-process-similar-companies-queue.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ProcessSimilarCompaniesQueueResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/company-linkedin/update",
    response_model=StagingCompanyLinkedInResponse,
    summary="Update staging company LinkedIn URL",
    description="Wrapper for Modal function: update_staging_company_linkedin"
)
async def update_staging_company_linkedin(request: StagingCompanyLinkedInRequest) -> StagingCompanyLinkedInResponse:
    """
    Update company_linkedin_url for a staging company by domain.

    Modal function: update_staging_company_linkedin
    Modal URL: https://bencrane--hq-master-data-ingest-update-vc-domain.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-update-vc-domain.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return StagingCompanyLinkedInResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/vc-domain/update",
    response_model=VCDomainUpdateResponse,
    summary="Update VC firm domain by name",
    description="Wrapper for Modal function: update_vc_domain"
)
async def update_vc_domain(request: VCDomainUpdateRequest) -> VCDomainUpdateResponse:
    """
    Update the domain for a VC firm by matching on name.

    Modal function: update_vc_domain
    Modal URL: https://bencrane--hq-master-data-ingest-upsert-core-company.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-upsert-core-company.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return VCDomainUpdateResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/core-company/upsert",
    response_model=CoreCompanyUpsertResponse,
    summary="Upsert company to core.companies",
    description="Wrapper for Modal function: upsert_core_company"
)
async def upsert_core_company(request: CoreCompanyUpsertRequest) -> CoreCompanyUpsertResponse:
    """
    Upsert a company to core.companies.

    Simple direct insert/update on domain.

    Modal function: upsert_core_company
    Modal URL: https://bencrane--hq-master-data-ingest-upsert-core-company.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-upsert-core-company.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CoreCompanyUpsertResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/core-company-full/upsert",
    response_model=CoreCompanyFullUpsertResponse,
    summary="Upsert company to all core dimension tables",
    description="Wrapper for Modal function: upsert_core_company_full"
)
async def upsert_core_company_full(request: CoreCompanyFullUpsertRequest) -> CoreCompanyFullUpsertResponse:
    """
    Upsert enriched company data to all core dimension tables.

    Writes to: core.companies, core.company_locations, core.company_industries,
    core.company_employee_ranges, core.company_linkedin_urls

    Modal function: upsert_core_company_full
    Modal URL: https://bencrane--hq-master-data-ingest-upsert-core-company-full.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-upsert-core-company-full.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CoreCompanyFullUpsertResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/icp-criteria/upsert",
    response_model=ICPCriteriaUpsertResponse,
    summary="Upsert ICP criteria for a company",
    description="Wrapper for Modal function: upsert_icp_criteria"
)
async def upsert_icp_criteria(request: ICPCriteriaUpsertRequest) -> ICPCriteriaUpsertResponse:
    """
    Upsert ICP filter criteria for a company to core.icp_criteria.

    Modal function: upsert_icp_criteria
    Modal URL: https://bencrane--hq-master-data-ingest-upsert-icp-criteria.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-upsert-icp-criteria.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ICPCriteriaUpsertResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/populate-name/backfill",
    response_model=BackfillCleanedCompanyNameResponse,
    summary="Backfill cleaned company names",
    description="Wrapper for Modal function: backfill_cleaned_company_name"
)
async def backfill_cleaned_company_name(request: BackfillCleanedCompanyNameRequest) -> BackfillCleanedCompanyNameResponse:
    """
    Backfill cleaned_name in core.companies from extracted.cleaned_company_names.

    Processes in batches to avoid timeouts.

    Modal function: backfill_cleaned_company_name
    Modal URL: https://bencrane--hq-master-data-ingest-backfill-cleaned-company-name.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-backfill-cleaned-company-name.modal.run"

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BackfillCleanedCompanyNameResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/populate-description/backfill",
    response_model=BackfillCompanyDescriptionsResponse,
    summary="Backfill company descriptions from multiple sources",
    description="Wrapper for Modal function: backfill_company_descriptions"
)
async def backfill_company_descriptions(request: BackfillCompanyDescriptionsRequest) -> BackfillCompanyDescriptionsResponse:
    """
    Backfill core.company_descriptions with priority:
    1. vc_portfolio.long_description
    2. company_firmographics.description
    3. company_discovery.description

    Modal function: backfill_company_descriptions
    Modal URL: https://bencrane--hq-master-data-ingest-backfill-company-descriptions.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-backfill-company-descriptions.modal.run"

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BackfillCompanyDescriptionsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/db/populate-location/backfill",
    response_model=BackfillPersonLocationResponse,
    summary="Backfill person locations from lookup table",
    description="Wrapper for Modal function: backfill_person_location"
)
async def backfill_person_location(request: BackfillPersonLocationRequest) -> BackfillPersonLocationResponse:
    """
    Backfill city/state/country in extracted.person_discovery from reference.location_lookup.

    Only updates records where city IS NULL. Use dry_run=True to preview.

    Modal function: backfill_person_location
    Modal URL: https://bencrane--hq-master-data-ingest-backfill-person-location.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-backfill-person-location.modal.run"

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BackfillPersonLocationResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/people/db/populate-matched-location/backfill",
    response_model=BackfillPersonMatchedLocationResponse,
    summary="Backfill person matched locations from lookup table",
    description="Wrapper for Modal function: backfill_person_matched_location"
)
async def backfill_person_matched_location(request: BackfillPersonMatchedLocationRequest) -> BackfillPersonMatchedLocationResponse:
    """
    Backfill matched_city/matched_state/matched_country in extracted.person_discovery.

    Processes up to `limit` records per call. Use dry_run=True to preview count.

    Modal function: backfill_person_matched_location
    Modal URL: https://bencrane--hq-master-data-ingest-backfill-person-matched--f1e270.modal.run
    """
    modal_url = "https://bencrane--hq-master-data-ingest-backfill-person-matched--f1e270.modal.run"

    async with httpx.AsyncClient(timeout=1800.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BackfillPersonMatchedLocationResponse(**response.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {e.response.text}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/ticker/ingest",
    response_model=CompanyTickerIngestResponse,
    summary="Ingest company ticker",
    description="Wrapper for Modal function: ingest_company_ticker"
)
async def ingest_company_ticker(request: CompanyTickerIngestRequest) -> CompanyTickerIngestResponse:
    """
    Ingest company ticker data.

    Stores raw payload, extracts ticker, upserts to reference.sec_company_info.

    Modal function: ingest_company_ticker
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-company-ticker.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-company-ticker.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json={
                    "domain": request.domain,
                    "ticker_payload": request.ticker_payload,
                    "clay_table_url": request.clay_table_url,
                }
            )
            response.raise_for_status()
            data = response.json()
            return CompanyTickerIngestResponse(**data)
        except httpx.HTTPStatusError as e:
            return CompanyTickerIngestResponse(
                success=False,
                error=f"Modal function error: {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/companies/db/public-ticker/backfill",
    response_model=BackfillPublicCompanyTickerResponse,
    summary="Update ticker for a public company",
    description="Updates the ticker column in core.company_public for a given domain"
)
async def backfill_public_company_ticker(request: BackfillPublicCompanyTickerRequest) -> BackfillPublicCompanyTickerResponse:
    """
    Update ticker for a public company in core.company_public.

    Used for backfilling SEC ticker symbols from Clay.
    """
    domain = request.domain.lower().strip().rstrip("/")
    ticker = request.ticker.upper().strip()

    if not domain:
        return BackfillPublicCompanyTickerResponse(success=False, error="domain is required")
    if not ticker:
        return BackfillPublicCompanyTickerResponse(success=False, error="ticker is required")

    pool = get_pool()

    result = await pool.execute("""
        UPDATE core.company_public
        SET ticker = $1
        WHERE domain = $2
    """, ticker, domain)

    rows_affected = int(result.split()[-1])

    if rows_affected == 0:
        return BackfillPublicCompanyTickerResponse(
            success=False,
            domain=domain,
            ticker=ticker,
            error=f"No company found with domain '{domain}' in core.company_public"
        )

    return BackfillPublicCompanyTickerResponse(
        success=True,
        domain=domain,
        ticker=ticker
    )


@router.post(
    "/client/leads/ingest",
    response_model=ClientLeadIngestResponse,
    summary="Ingest a client lead",
    description="Ingests lead data into client.leads, client.leads_people, and client.leads_companies"
)
async def ingest_client_lead(request: ClientLeadIngestRequest) -> ClientLeadIngestResponse:
    """
    Ingest a lead for a client.

    Writes to three tables:
    - client.leads (denormalized, all fields)
    - client.leads_people (normalized person data)
    - client.leads_companies (normalized company data)
    """
    pool = get_pool()

    client_domain = request.client_domain.lower().strip() if request.client_domain else None
    if not client_domain:
        return ClientLeadIngestResponse(success=False, error="client_domain is required")

    company_domain = request.company_domain.lower().strip().rstrip("/") if request.company_domain else None
    person_linkedin_url = request.person_linkedin_url.strip() if request.person_linkedin_url else None
    company_linkedin_url = request.company_linkedin_url.strip() if request.company_linkedin_url else None

    try:
        # Insert into client.leads (denormalized)
        lead_row = await pool.fetchrow("""
            INSERT INTO client.leads (
                client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                company_name, company_linkedin_url, source,
                client_form_id, client_form_title
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """,
            client_domain, request.first_name, request.last_name, request.full_name,
            person_linkedin_url, request.work_email, company_domain,
            request.company_name, company_linkedin_url, request.source,
            request.client_form_id, request.client_form_title
        )
        lead_id = str(lead_row["id"])

        # Insert into client.leads_people (normalized)
        person_row = await pool.fetchrow("""
            INSERT INTO client.leads_people (
                client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                source, client_form_id, client_form_title
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """,
            client_domain, request.first_name, request.last_name, request.full_name,
            person_linkedin_url, request.work_email, company_domain,
            request.source, request.client_form_id, request.client_form_title
        )
        person_id = str(person_row["id"])

        # Insert into client.leads_companies (normalized) - only if we have company data
        company_id = None
        if company_domain or request.company_name or company_linkedin_url:
            company_row = await pool.fetchrow("""
                INSERT INTO client.leads_companies (
                    client_domain, company_domain, company_name,
                    company_linkedin_url, source, client_form_id, client_form_title
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """,
                client_domain, company_domain, request.company_name,
                company_linkedin_url, request.source,
                request.client_form_id, request.client_form_title
            )
            company_id = str(company_row["id"])

        return ClientLeadIngestResponse(
            success=True,
            lead_id=lead_id,
            person_id=person_id,
            company_id=company_id
        )

    except Exception as e:
        return ClientLeadIngestResponse(
            success=False,
            error=str(e)
        )


@router.post(
    "/reference/job-title/update",
    response_model=JobTitleUpdateResponse,
    summary="Add job title mapping to lookup table",
    description="Adds a new entry to reference.job_title_lookup"
)
async def update_job_title_lookup(request: JobTitleUpdateRequest) -> JobTitleUpdateResponse:
    """
    Add a new job title mapping to reference.job_title_lookup.

    Used when a title lookup returns no match and Clay has cleaned/classified the title.
    """
    pool = get_pool()

    latest_title = request.latest_title.strip() if request.latest_title else None
    cleaned_job_title = request.cleaned_job_title.strip() if request.cleaned_job_title else None

    if not latest_title:
        return JobTitleUpdateResponse(success=False, error="latest_title is required")
    if not cleaned_job_title:
        return JobTitleUpdateResponse(success=False, error="cleaned_job_title is required")

    try:
        await pool.execute("""
            INSERT INTO reference.job_title_lookup (
                latest_title, cleaned_job_title, seniority_level, job_function, status
            ) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (latest_title) DO UPDATE SET
                cleaned_job_title = EXCLUDED.cleaned_job_title,
                seniority_level = EXCLUDED.seniority_level,
                job_function = EXCLUDED.job_function,
                status = EXCLUDED.status
        """,
            latest_title, cleaned_job_title, request.seniority_level,
            request.job_function, request.status
        )

        return JobTitleUpdateResponse(
            success=True,
            latest_title=latest_title,
            cleaned_job_title=cleaned_job_title,
            seniority_level=request.seniority_level,
            job_function=request.job_function
        )

    except Exception as e:
        return JobTitleUpdateResponse(success=False, error=str(e))


@router.post(
    "/reference/location/update",
    response_model=LocationUpdateResponse,
    summary="Add location mapping to lookup table",
    description="Adds a new entry to reference.location_lookup"
)
async def update_location_lookup(request: LocationUpdateRequest) -> LocationUpdateResponse:
    """
    Add a new location mapping to reference.location_lookup.

    Used when a location lookup returns no match and Clay has parsed the location.
    """
    pool = get_pool()

    location_name = request.location_name.strip() if request.location_name else None

    if not location_name:
        return LocationUpdateResponse(success=False, error="location_name is required")

    # Derive has_* fields if not provided
    has_city = request.has_city if request.has_city is not None else bool(request.city)
    has_state = request.has_state if request.has_state is not None else bool(request.state)
    has_country = request.has_country if request.has_country is not None else bool(request.country)

    try:
        await pool.execute("""
            INSERT INTO reference.location_lookup (
                location_name, city, state, country, has_city, has_state, has_country
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (location_name) DO UPDATE SET
                city = EXCLUDED.city,
                state = EXCLUDED.state,
                country = EXCLUDED.country,
                has_city = EXCLUDED.has_city,
                has_state = EXCLUDED.has_state,
                has_country = EXCLUDED.has_country
        """,
            location_name, request.city, request.state, request.country,
            has_city, has_state, has_country
        )

        return LocationUpdateResponse(
            success=True,
            location_name=location_name,
            city=request.city,
            state=request.state,
            country=request.country
        )

    except Exception as e:
        return LocationUpdateResponse(success=False, error=str(e))
