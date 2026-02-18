"""
Run Router - API wrappers for Modal serverless functions

This router provides API endpoints that wrap Modal functions,
giving a consistent api.revenueinfra.com interface for all workflows.

Naming convention:
    /run/{entity}/{platform}/{workflow}/{action}

Example:
    POST /run/companies/clay-native/find-companies/ingest
    POST /run/companies/openai-native/b2b-b2c/classify/db-direct
"""

import httpx
import csv
import io
import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
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
    workflow_slug: str


class CaseStudyExtractionResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    case_study_id: Optional[str] = None
    origin_company_name: Optional[str] = None
    origin_company_domain: Optional[str] = None
    company_customer_name: Optional[str] = None
    champion_count: Optional[int] = None
    champions: Optional[list] = None
    customer_domain_found: Optional[bool] = None
    customer_domain: Optional[str] = None
    article_title: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
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


class SimilarCompaniesLookupRequest(BaseModel):
    domain: str


class SimilarCompaniesLookupResponse(BaseModel):
    success: bool
    found: Optional[bool] = None
    domain: Optional[str] = None
    similar_count: Optional[int] = None
    error: Optional[str] = None


class CompanyEnrichSimilarPreviewResultsResponse(BaseModel):
    success: bool
    input_domain: Optional[str] = None
    raw_id: Optional[str] = None
    items_received: Optional[int] = None
    extracted_count: Optional[int] = None
    core_count: Optional[int] = None
    error: Optional[str] = None


class ResolveCustomerDomainRequest(BaseModel):
    customer_name: str
    origin_company_name: str
    origin_company_domain: str


class ResolveCustomerDomainResponse(BaseModel):
    success: bool
    customer_name: Optional[str] = None
    origin_company_name: Optional[str] = None
    origin_company_domain: Optional[str] = None
    customer_domain: Optional[str] = None
    confidence: Optional[str] = None
    reasoning: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None


class CompanyBusinessModelLookupRequest(BaseModel):
    domain: str


class CompanyBusinessModelLookupResponse(BaseModel):
    success: bool
    found: Optional[bool] = None
    domain: Optional[str] = None
    is_b2b: Optional[bool] = None
    is_b2c: Optional[bool] = None
    error: Optional[str] = None


class CompanyDescriptionLookupRequest(BaseModel):
    domain: str


class CompanyDescriptionLookupResponse(BaseModel):
    success: bool
    found: Optional[bool] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class CompanyCustomersLookupRequest(BaseModel):
    domain: str


class CustomerInfo(BaseModel):
    origin_company_name: Optional[str] = None
    origin_company_domain: Optional[str] = None
    customer_name: Optional[str] = None
    customer_domain: Optional[str] = None
    customer_linkedin_url: Optional[str] = None


class CompanyCustomersLookupResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    customer_count: Optional[int] = None
    customers: Optional[list[CustomerInfo]] = None
    error: Optional[str] = None


class ChampionInfo(BaseModel):
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    case_study_url: Optional[str] = None
    source: Optional[str] = None


class CaseStudyChampionsLookupRequest(BaseModel):
    domain: str


class CaseStudyChampionsLookupResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    champion_count: Optional[int] = None
    champions: Optional[list[ChampionInfo]] = None
    error: Optional[str] = None


class ChampionDetailedInfo(BaseModel):
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    case_study_url: Optional[str] = None
    source: Optional[str] = None
    testimonial: Optional[str] = None


class ChampionsDetailedLookupRequest(BaseModel):
    domain: str


class ChampionsDetailedLookupResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    champion_count: Optional[int] = None
    champions: Optional[list[ChampionDetailedInfo]] = None
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


class BackfillParallelToCoreRequest(BaseModel):
    batch_size: int = 5000
    backfill_customers: bool = True
    backfill_champions: bool = True


class BackfillParallelToCoreResponse(BaseModel):
    success: bool
    customers_updated: Optional[int] = None
    champions_inserted: Optional[int] = None
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
    ticker_payload: Any  # Can be string "AAPL" or dict {"ticker": "AAPL"}
    clay_table_url: Optional[str] = None


class CompanyTickerIngestResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    ticker: Optional[str] = None
    raw_payload_id: Optional[str] = None
    error: Optional[str] = None


class SECFinancialsIngestRequest(BaseModel):
    domain: str


class SECFinancialsLatestPeriod(BaseModel):
    period_end: Optional[str] = None
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    revenue: Optional[int] = None
    net_income: Optional[int] = None


class SECFinancialsIngestResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    cik: Optional[str] = None
    ticker: Optional[str] = None
    sec_company_name: Optional[str] = None
    raw_payload_id: Optional[str] = None
    periods_extracted: Optional[int] = None
    latest_period: Optional[SECFinancialsLatestPeriod] = None
    error: Optional[str] = None


class SECFilingsRequest(BaseModel):
    domain: str


class SECFilingInfo(BaseModel):
    filing_date: Optional[str] = None
    report_date: Optional[str] = None
    accession_number: Optional[str] = None
    document_url: Optional[str] = None
    items: Optional[str] = None


class SECFilingsData(BaseModel):
    latest_10q: Optional[SECFilingInfo] = None
    latest_10k: Optional[SECFilingInfo] = None
    recent_8k_executive_changes: Optional[List[SECFilingInfo]] = None
    recent_8k_earnings: Optional[List[SECFilingInfo]] = None
    recent_8k_material_contracts: Optional[List[SECFilingInfo]] = None


class SECFilingsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    cik: Optional[str] = None
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    filings: Optional[SECFilingsData] = None
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


class TargetClientLeadIngestRequest(BaseModel):
    target_client_domain: str
    form_id: Optional[str] = None
    form_title: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    work_email: Optional[str] = None
    company_domain: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source: Optional[str] = None


class TargetClientLeadIngestResponse(BaseModel):
    success: bool
    lead_id: Optional[str] = None
    person_id: Optional[str] = None
    company_id: Optional[str] = None
    core_company_id: Optional[str] = None
    core_person_id: Optional[str] = None
    error: Optional[str] = None


class TargetClientLeadsListRequest(BaseModel):
    target_client_domain: str
    source: Optional[str] = None  # Optional filter by source


class TargetClientLeadLinkRequest(BaseModel):
    target_client_domain: str
    company_domain: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    person_email: Optional[str] = None
    source: Optional[str] = "demo"
    form_id: Optional[str] = None
    form_title: Optional[str] = None


class TargetClientLeadLinkResponse(BaseModel):
    success: bool
    lead_id: Optional[str] = None
    core_company_id: Optional[str] = None
    core_person_id: Optional[str] = None
    company_found: bool = False
    person_found: bool = False
    error: Optional[str] = None


class TargetClientLeadLinkBatchItem(BaseModel):
    company_domain: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    person_email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None


class TargetClientLeadLinkBatchRequest(BaseModel):
    target_client_domain: str
    leads: List[TargetClientLeadLinkBatchItem]
    source: Optional[str] = "csv_import"
    form_id: Optional[str] = None
    form_title: Optional[str] = None


class TargetClientLeadLinkBatchResultItem(BaseModel):
    index: int
    success: bool
    lead_id: Optional[str] = None
    core_company_id: Optional[str] = None
    core_person_id: Optional[str] = None
    company_found: bool = False
    person_found: bool = False
    error: Optional[str] = None


class TargetClientLeadLinkBatchResponse(BaseModel):
    success: bool
    total: int = 0
    linked: int = 0
    failed: int = 0
    results: List[TargetClientLeadLinkBatchResultItem] = []
    error: Optional[str] = None


class TargetClientLeadEnrichedCompany(BaseModel):
    id: Optional[str] = None
    domain: Optional[str] = None
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class TargetClientLeadEnrichedPerson(BaseModel):
    id: Optional[str] = None
    full_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    title: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None


class TargetClientLead(BaseModel):
    id: str
    target_client_domain: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    work_email: Optional[str] = None
    company_domain: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source: Optional[str] = None
    form_id: Optional[str] = None
    form_title: Optional[str] = None
    created_at: Optional[str] = None
    core_company_id: Optional[str] = None
    core_person_id: Optional[str] = None
    enriched_company: Optional[TargetClientLeadEnrichedCompany] = None
    enriched_person: Optional[TargetClientLeadEnrichedPerson] = None


class TargetClientLeadsListResponse(BaseModel):
    success: bool
    leads: List[TargetClientLead] = []
    count: int = 0
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
    summary="[DEPRECATED] Ingest company customers (variant 1) - Use customers-of-3 instead",
    description="DEPRECATED: Use /run/companies/claygent/customers-of-3/ingest instead",
    deprecated=True
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
    summary="[DEPRECATED] Ingest company customers (variant 2) - Use customers-of-3 instead",
    description="DEPRECATED: Use /run/companies/claygent/customers-of-3/ingest instead",
    deprecated=True
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
    summary="[DEPRECATED] Ingest company customers (variant 4) - Use customers-of-3 instead",
    description="DEPRECATED: Use /run/companies/claygent/customers-of-3/ingest instead",
    deprecated=True
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
    "/companies/db/company-business-model/lookup",
    response_model=CompanyBusinessModelLookupResponse,
    summary="Lookup company B2B/B2C classification by domain",
    description="Wrapper for Modal function: lookup_company_business_model"
)
async def lookup_company_business_model(request: CompanyBusinessModelLookupRequest) -> CompanyBusinessModelLookupResponse:
    """
    Lookup company B2B/B2C classification from core.company_business_model.

    Modal function: lookup_company_business_model
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-company-business-model.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-company-business-model.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyBusinessModelLookupResponse(**response.json())
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
    "/companies/db/similar-companies/lookup",
    response_model=SimilarCompaniesLookupResponse,
    summary="Check if similar companies have been generated for a domain",
    description="Wrapper for Modal function: lookup_similar_companies"
)
async def lookup_similar_companies(request: SimilarCompaniesLookupRequest) -> SimilarCompaniesLookupResponse:
    """
    Check if core.company_similar_companies_preview has results for a domain.

    Modal function: lookup_similar_companies
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-similar-companies.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-similar-companies.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return SimilarCompaniesLookupResponse(**response.json())
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
    "/companies/companyenrich/similar-companies-preview-results/ingest",
    response_model=CompanyEnrichSimilarPreviewResultsResponse,
    summary="Ingest CompanyEnrich similar companies preview results from Clay",
    description="Wrapper for Modal function: ingest_companyenrich_similar_preview_results"
)
async def ingest_companyenrich_similar_preview_results(data: dict) -> CompanyEnrichSimilarPreviewResultsResponse:
    """
    Receive CompanyEnrich similar/preview results from Clay.

    Modal function: ingest_companyenrich_similar_preview_results
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-companyenrich-sim-cbc297.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-companyenrich-sim-cbc297.modal.run"

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=data
            )
            response.raise_for_status()
            return CompanyEnrichSimilarPreviewResultsResponse(**response.json())
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
    "/companies/db/company-description/lookup",
    response_model=CompanyDescriptionLookupResponse,
    summary="Lookup company description by domain",
    description="Wrapper for Modal function: lookup_company_description"
)
async def lookup_company_description(request: CompanyDescriptionLookupRequest) -> CompanyDescriptionLookupResponse:
    """
    Lookup company description and tagline from core.company_descriptions.

    Modal function: lookup_company_description
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-company-description.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-company-description.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CompanyDescriptionLookupResponse(**response.json())
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
    "/companies/sec/financials/fetch",
    response_model=SECFinancialsIngestResponse,
    summary="Fetch SEC financials for a company",
    description="Wrapper for Modal function: ingest_sec_financials"
)
async def fetch_sec_financials(request: SECFinancialsIngestRequest) -> SECFinancialsIngestResponse:
    """
    Fetch and store SEC EDGAR financial data for a public company.

    Looks up CIK from existing ticker data, fetches CompanyFacts from SEC,
    stores raw payload, extracts key financial metrics by period.

    Modal function: ingest_sec_financials
    Modal URL: https://bencrane--hq-master-data-ingest-ingest-sec-financials.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-ingest-sec-financials.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json={"domain": request.domain}
            )
            result = response.json()

            latest = result.get("latest_period")
            latest_period = None
            if latest:
                latest_period = SECFinancialsLatestPeriod(
                    period_end=latest.get("period_end"),
                    fiscal_year=latest.get("fiscal_year"),
                    fiscal_period=latest.get("fiscal_period"),
                    revenue=latest.get("revenue"),
                    net_income=latest.get("net_income"),
                )

            return SECFinancialsIngestResponse(
                success=result.get("success", False),
                domain=result.get("domain"),
                cik=result.get("cik"),
                ticker=result.get("ticker"),
                sec_company_name=result.get("sec_company_name"),
                raw_payload_id=result.get("raw_payload_id"),
                periods_extracted=result.get("periods_extracted"),
                latest_period=latest_period,
                error=result.get("error"),
            )
        except Exception as e:
            return SECFinancialsIngestResponse(
                success=False,
                domain=request.domain,
                error=str(e),
            )


@router.post(
    "/companies/sec/filings/fetch",
    response_model=SECFilingsResponse,
    summary="Fetch SEC filings for a company",
    description="Wrapper for Modal function: fetch_sec_filings"
)
async def fetch_sec_filings(request: SECFilingsRequest) -> SECFilingsResponse:
    """
    Fetch SEC filing metadata for a public company.

    Returns filtered filings relevant for sales briefings:
    - Latest 10-Q (quarterly report)
    - Latest 10-K (annual report)
    - Recent 8-Ks with executive changes (5.02), earnings (2.02), material contracts (1.01)

    Each filing includes a document_url that can be passed to an LLM for summarization.

    Modal function: fetch_sec_filings
    Modal URL: https://bencrane--hq-master-data-ingest-fetch-sec-filings.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-fetch-sec-filings.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json={"domain": request.domain}
            )
            result = response.json()

            # Parse filings into typed models
            filings_data = None
            if result.get("filings"):
                raw_filings = result["filings"]

                def parse_filing(f: dict) -> SECFilingInfo:
                    return SECFilingInfo(
                        filing_date=f.get("filing_date"),
                        report_date=f.get("report_date"),
                        accession_number=f.get("accession_number"),
                        document_url=f.get("document_url"),
                        items=f.get("items"),
                    )

                filings_data = SECFilingsData(
                    latest_10q=parse_filing(raw_filings["latest_10q"]) if raw_filings.get("latest_10q") else None,
                    latest_10k=parse_filing(raw_filings["latest_10k"]) if raw_filings.get("latest_10k") else None,
                    recent_8k_executive_changes=[parse_filing(f) for f in raw_filings.get("recent_8k_executive_changes", [])],
                    recent_8k_earnings=[parse_filing(f) for f in raw_filings.get("recent_8k_earnings", [])],
                    recent_8k_material_contracts=[parse_filing(f) for f in raw_filings.get("recent_8k_material_contracts", [])],
                )

            return SECFilingsResponse(
                success=result.get("success", False),
                domain=result.get("domain"),
                cik=result.get("cik"),
                ticker=result.get("ticker"),
                company_name=result.get("company_name"),
                filings=filings_data,
                error=result.get("error"),
            )
        except Exception as e:
            return SECFilingsResponse(
                success=False,
                domain=request.domain,
                error=str(e),
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
    "/target-client/leads/ingest",
    response_model=TargetClientLeadIngestResponse,
    summary="Ingest a lead for a target client (demo/prospect)",
    description="Ingests lead data into target_client.leads, target_client.leads_people, and target_client.leads_companies"
)
async def ingest_target_client_lead(request: TargetClientLeadIngestRequest) -> TargetClientLeadIngestResponse:
    """
    Ingest a lead for a target client (demo/prospect).

    Writes to three tables:
    - target_client.leads (denormalized, all fields)
    - target_client.leads_people (normalized person data)
    - target_client.leads_companies (normalized company data)

    Use this for demos and prospects. Use /client/leads/ingest for paying clients.
    """
    pool = get_pool()

    target_client_domain = request.target_client_domain.lower().strip() if request.target_client_domain else None
    if not target_client_domain:
        return TargetClientLeadIngestResponse(success=False, error="target_client_domain is required")

    company_domain = request.company_domain.lower().strip().rstrip("/") if request.company_domain else None
    person_linkedin_url = request.person_linkedin_url.strip() if request.person_linkedin_url else None
    company_linkedin_url = request.company_linkedin_url.strip() if request.company_linkedin_url else None
    work_email = request.work_email.lower().strip() if request.work_email else None

    try:
        # Look up core_company_id from core.companies by domain
        core_company_id = None
        if company_domain:
            company_lookup = await pool.fetchrow(
                "SELECT id FROM core.companies WHERE domain = $1 LIMIT 1",
                company_domain
            )
            if company_lookup:
                core_company_id = company_lookup["id"]

        # Look up core_person_id from core.people by linkedin_url or email
        core_person_id = None
        if person_linkedin_url:
            person_lookup = await pool.fetchrow(
                "SELECT id FROM core.people WHERE linkedin_url = $1 LIMIT 1",
                person_linkedin_url
            )
            if person_lookup:
                core_person_id = person_lookup["id"]
        if not core_person_id and work_email:
            person_lookup = await pool.fetchrow(
                "SELECT id FROM core.people WHERE work_email = $1 LIMIT 1",
                work_email
            )
            if person_lookup:
                core_person_id = person_lookup["id"]

        # Insert into target_client.leads (denormalized)
        lead_row = await pool.fetchrow("""
            INSERT INTO target_client.leads (
                target_client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                company_name, company_linkedin_url, source,
                form_id, form_title, core_company_id, core_person_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id
        """,
            target_client_domain, request.first_name, request.last_name, request.full_name,
            person_linkedin_url, work_email, company_domain,
            request.company_name, company_linkedin_url, request.source,
            request.form_id, request.form_title, core_company_id, core_person_id
        )
        lead_id = str(lead_row["id"])

        # Insert into target_client.leads_people (normalized)
        person_row = await pool.fetchrow("""
            INSERT INTO target_client.leads_people (
                target_client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                source, form_id, form_title
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """,
            target_client_domain, request.first_name, request.last_name, request.full_name,
            person_linkedin_url, request.work_email, company_domain,
            request.source, request.form_id, request.form_title
        )
        person_id = str(person_row["id"])

        # Insert into target_client.leads_companies (normalized) - only if we have company data
        company_id = None
        if company_domain or request.company_name or company_linkedin_url:
            company_row = await pool.fetchrow("""
                INSERT INTO target_client.leads_companies (
                    target_client_domain, company_domain, company_name,
                    company_linkedin_url, source, form_id, form_title
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """,
                target_client_domain, company_domain, request.company_name,
                company_linkedin_url, request.source,
                request.form_id, request.form_title
            )
            company_id = str(company_row["id"])

        return TargetClientLeadIngestResponse(
            success=True,
            lead_id=lead_id,
            person_id=person_id,
            company_id=company_id,
            core_company_id=str(core_company_id) if core_company_id else None,
            core_person_id=str(core_person_id) if core_person_id else None
        )

    except Exception as e:
        return TargetClientLeadIngestResponse(
            success=False,
            error=str(e)
        )


@router.post(
    "/target-client/leads/list",
    response_model=TargetClientLeadsListResponse,
    summary="List leads for a target client (demo/prospect)",
    description="Returns all leads for a target_client_domain, optionally filtered by source"
)
async def list_target_client_leads(request: TargetClientLeadsListRequest) -> TargetClientLeadsListResponse:
    """
    List leads for a target client (demo/prospect).

    Queries target_client.leads and returns all leads for the given domain.
    Optionally filter by source (e.g., 'contact_form', 'csv_upload').
    """
    pool = get_pool()

    target_client_domain = request.target_client_domain.lower().strip() if request.target_client_domain else None
    if not target_client_domain:
        return TargetClientLeadsListResponse(success=False, error="target_client_domain is required")

    try:
        # Build query with LEFT JOINs to core tables for enriched data
        base_query = """
            SELECT
                l.id, l.target_client_domain, l.first_name, l.last_name, l.full_name,
                l.person_linkedin_url, l.work_email, l.company_domain, l.company_name,
                l.company_linkedin_url, l.source, l.form_id, l.form_title, l.created_at,
                l.core_company_id, l.core_person_id,
                -- Enriched company fields
                c.id as ec_id, c.domain as ec_domain, c.name as ec_name,
                c.linkedin_url as ec_linkedin_url, c.industry as ec_industry,
                c.employee_count as ec_employee_count, c.city as ec_city,
                c.state as ec_state, c.country as ec_country,
                -- Enriched person fields
                p.id as ep_id, p.full_name as ep_full_name, p.linkedin_url as ep_linkedin_url,
                p.title as ep_title, p.seniority as ep_seniority, p.department as ep_department
            FROM target_client.leads l
            LEFT JOIN core.companies c ON l.core_company_id = c.id
            LEFT JOIN core.people p ON l.core_person_id = p.id
            WHERE l.target_client_domain = $1
        """

        if request.source:
            rows = await pool.fetch(
                base_query + " AND l.source = $2 ORDER BY l.created_at DESC",
                target_client_domain, request.source
            )
        else:
            rows = await pool.fetch(
                base_query + " ORDER BY l.created_at DESC",
                target_client_domain
            )

        leads = []
        for row in rows:
            # Build enriched company if we have core_company_id
            enriched_company = None
            if row["core_company_id"]:
                enriched_company = TargetClientLeadEnrichedCompany(
                    id=str(row["ec_id"]) if row["ec_id"] else None,
                    domain=row["ec_domain"],
                    name=row["ec_name"],
                    linkedin_url=row["ec_linkedin_url"],
                    industry=row["ec_industry"],
                    employee_count=row["ec_employee_count"],
                    city=row["ec_city"],
                    state=row["ec_state"],
                    country=row["ec_country"],
                )

            # Build enriched person if we have core_person_id
            enriched_person = None
            if row["core_person_id"]:
                enriched_person = TargetClientLeadEnrichedPerson(
                    id=str(row["ep_id"]) if row["ep_id"] else None,
                    full_name=row["ep_full_name"],
                    linkedin_url=row["ep_linkedin_url"],
                    title=row["ep_title"],
                    seniority=row["ep_seniority"],
                    department=row["ep_department"],
                )

            leads.append(TargetClientLead(
                id=str(row["id"]),
                target_client_domain=row["target_client_domain"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                full_name=row["full_name"],
                person_linkedin_url=row["person_linkedin_url"],
                work_email=row["work_email"],
                company_domain=row["company_domain"],
                company_name=row["company_name"],
                company_linkedin_url=row["company_linkedin_url"],
                source=row["source"],
                form_id=row["form_id"],
                form_title=row["form_title"],
                created_at=row["created_at"].isoformat() if row["created_at"] else None,
                core_company_id=str(row["core_company_id"]) if row["core_company_id"] else None,
                core_person_id=str(row["core_person_id"]) if row["core_person_id"] else None,
                enriched_company=enriched_company,
                enriched_person=enriched_person,
            ))

        return TargetClientLeadsListResponse(
            success=True,
            leads=leads,
            count=len(leads)
        )

    except Exception as e:
        return TargetClientLeadsListResponse(
            success=False,
            error=str(e)
        )


@router.post(
    "/target-client/leads/link",
    response_model=TargetClientLeadLinkResponse,
    summary="Link existing core data to a target client lead",
    description="Creates a target_client.leads record pointing to existing core.companies and core.people records"
)
async def link_target_client_lead(request: TargetClientLeadLinkRequest) -> TargetClientLeadLinkResponse:
    """
    Link existing enriched data to a target client lead for demos.

    Looks up existing records in core.companies and core.people,
    then creates a target_client.leads record with FKs pointing to them.

    No enrichment runs - just links existing data.
    """
    pool = get_pool()

    target_client_domain = request.target_client_domain.lower().strip() if request.target_client_domain else None
    if not target_client_domain:
        return TargetClientLeadLinkResponse(success=False, error="target_client_domain is required")

    company_domain = request.company_domain.lower().strip().rstrip("/") if request.company_domain else None
    person_linkedin_url = request.person_linkedin_url.strip() if request.person_linkedin_url else None
    person_email = request.person_email.lower().strip() if request.person_email else None

    try:
        # Look up core_company_id from core.companies by domain
        core_company_id = None
        company_name = None
        company_linkedin_url = None
        company_found = False
        if company_domain:
            company_lookup = await pool.fetchrow(
                "SELECT id, name, linkedin_url FROM core.companies WHERE domain = $1 LIMIT 1",
                company_domain
            )
            if company_lookup:
                core_company_id = company_lookup["id"]
                company_name = company_lookup["name"]
                company_linkedin_url = company_lookup["linkedin_url"]
                company_found = True

        # Look up core_person_id from core.people by linkedin_url or email
        core_person_id = None
        first_name = None
        last_name = None
        full_name = None
        work_email = None
        person_found = False

        if person_linkedin_url:
            person_lookup = await pool.fetchrow(
                "SELECT id, first_name, last_name, full_name, work_email FROM core.people WHERE linkedin_url = $1 LIMIT 1",
                person_linkedin_url
            )
            if person_lookup:
                core_person_id = person_lookup["id"]
                first_name = person_lookup["first_name"]
                last_name = person_lookup["last_name"]
                full_name = person_lookup["full_name"]
                work_email = person_lookup["work_email"]
                person_found = True

        if not core_person_id and person_email:
            person_lookup = await pool.fetchrow(
                "SELECT id, first_name, last_name, full_name, linkedin_url, work_email FROM core.people WHERE work_email = $1 LIMIT 1",
                person_email
            )
            if person_lookup:
                core_person_id = person_lookup["id"]
                first_name = person_lookup["first_name"]
                last_name = person_lookup["last_name"]
                full_name = person_lookup["full_name"]
                person_linkedin_url = person_lookup["linkedin_url"]
                work_email = person_lookup["work_email"]
                person_found = True

        # Must find at least one
        if not core_company_id and not core_person_id:
            return TargetClientLeadLinkResponse(
                success=False,
                error="No matching company or person found in core tables",
                company_found=False,
                person_found=False
            )

        # Insert into target_client.leads with FKs
        lead_row = await pool.fetchrow("""
            INSERT INTO target_client.leads (
                target_client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                company_name, company_linkedin_url, source,
                form_id, form_title, core_company_id, core_person_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id
        """,
            target_client_domain, first_name, last_name, full_name,
            person_linkedin_url, work_email, company_domain,
            company_name, company_linkedin_url, request.source,
            request.form_id, request.form_title, core_company_id, core_person_id
        )
        lead_id = str(lead_row["id"])

        return TargetClientLeadLinkResponse(
            success=True,
            lead_id=lead_id,
            core_company_id=str(core_company_id) if core_company_id else None,
            core_person_id=str(core_person_id) if core_person_id else None,
            company_found=company_found,
            person_found=person_found
        )

    except Exception as e:
        return TargetClientLeadLinkResponse(
            success=False,
            error=str(e)
        )


@router.post(
    "/target-client/leads/link-batch",
    response_model=TargetClientLeadLinkBatchResponse,
    summary="Link batch of existing core data to target client leads",
    description="Creates multiple target_client.leads records from a CSV import, linking to existing core data"
)
async def link_target_client_leads_batch(request: TargetClientLeadLinkBatchRequest) -> TargetClientLeadLinkBatchResponse:
    """
    Link a batch of existing enriched data to target client leads for demos.

    Ideal for CSV imports where work_email matches existing core.people records.
    Looks up each lead by email/linkedin, then creates target_client.leads with FKs.
    """
    pool = get_pool()

    target_client_domain = request.target_client_domain.lower().strip() if request.target_client_domain else None
    if not target_client_domain:
        return TargetClientLeadLinkBatchResponse(success=False, error="target_client_domain is required")

    if not request.leads:
        return TargetClientLeadLinkBatchResponse(success=False, error="No leads provided")

    results = []
    linked = 0
    failed = 0

    for idx, lead in enumerate(request.leads):
        try:
            company_domain = lead.company_domain.lower().strip().rstrip("/") if lead.company_domain else None
            person_linkedin_url = lead.person_linkedin_url.strip() if lead.person_linkedin_url else None
            person_email = lead.person_email.lower().strip() if lead.person_email else None

            # Look up core_company_id
            core_company_id = None
            company_name = None
            company_linkedin_url = None
            company_found = False
            if company_domain:
                company_lookup = await pool.fetchrow(
                    "SELECT id, name, linkedin_url FROM core.companies WHERE domain = $1 LIMIT 1",
                    company_domain
                )
                if company_lookup:
                    core_company_id = company_lookup["id"]
                    company_name = company_lookup["name"]
                    company_linkedin_url = company_lookup["linkedin_url"]
                    company_found = True

            # Look up core_person_id - prefer email for CSV imports
            core_person_id = None
            first_name = lead.first_name
            last_name = lead.last_name
            full_name = lead.full_name
            work_email = person_email
            person_found = False

            if person_email:
                person_lookup = await pool.fetchrow(
                    "SELECT id, first_name, last_name, full_name, linkedin_url, work_email, company_domain FROM core.people WHERE work_email = $1 LIMIT 1",
                    person_email
                )
                if person_lookup:
                    core_person_id = person_lookup["id"]
                    first_name = first_name or person_lookup["first_name"]
                    last_name = last_name or person_lookup["last_name"]
                    full_name = full_name or person_lookup["full_name"]
                    person_linkedin_url = person_linkedin_url or person_lookup["linkedin_url"]
                    # Also grab company_domain from person if not provided
                    if not company_domain and person_lookup["company_domain"]:
                        company_domain = person_lookup["company_domain"]
                        # Try to look up company now
                        company_lookup = await pool.fetchrow(
                            "SELECT id, name, linkedin_url FROM core.companies WHERE domain = $1 LIMIT 1",
                            company_domain
                        )
                        if company_lookup:
                            core_company_id = company_lookup["id"]
                            company_name = company_lookup["name"]
                            company_linkedin_url = company_lookup["linkedin_url"]
                            company_found = True
                    person_found = True

            if not core_person_id and person_linkedin_url:
                person_lookup = await pool.fetchrow(
                    "SELECT id, first_name, last_name, full_name, work_email FROM core.people WHERE linkedin_url = $1 LIMIT 1",
                    person_linkedin_url
                )
                if person_lookup:
                    core_person_id = person_lookup["id"]
                    first_name = first_name or person_lookup["first_name"]
                    last_name = last_name or person_lookup["last_name"]
                    full_name = full_name or person_lookup["full_name"]
                    work_email = work_email or person_lookup["work_email"]
                    person_found = True

            # Must find at least person for CSV import
            if not core_person_id:
                results.append(TargetClientLeadLinkBatchResultItem(
                    index=idx,
                    success=False,
                    error="No matching person found in core.people",
                    company_found=company_found,
                    person_found=False
                ))
                failed += 1
                continue

            # Insert into target_client.leads with FKs
            lead_row = await pool.fetchrow("""
                INSERT INTO target_client.leads (
                    target_client_domain, first_name, last_name, full_name,
                    person_linkedin_url, work_email, company_domain,
                    company_name, company_linkedin_url, source,
                    form_id, form_title, core_company_id, core_person_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
            """,
                target_client_domain, first_name, last_name, full_name,
                person_linkedin_url, work_email, company_domain,
                company_name, company_linkedin_url, request.source,
                request.form_id, request.form_title, core_company_id, core_person_id
            )
            lead_id = str(lead_row["id"])

            results.append(TargetClientLeadLinkBatchResultItem(
                index=idx,
                success=True,
                lead_id=lead_id,
                core_company_id=str(core_company_id) if core_company_id else None,
                core_person_id=str(core_person_id) if core_person_id else None,
                company_found=company_found,
                person_found=person_found
            ))
            linked += 1

        except Exception as e:
            results.append(TargetClientLeadLinkBatchResultItem(
                index=idx,
                success=False,
                error=str(e)
            ))
            failed += 1

    return TargetClientLeadLinkBatchResponse(
        success=True,
        total=len(request.leads),
        linked=linked,
        failed=failed,
        results=results
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


# =============================================================================
# LinkedIn Job Video Extraction
# =============================================================================

class LinkedInJobVideoResponse(BaseModel):
    success: bool
    raw_video_id: Optional[str] = None
    video_filename: Optional[str] = None
    video_duration_seconds: Optional[float] = None
    frames_extracted: Optional[int] = None
    jobs_extracted: Optional[int] = None
    tokens_used: Optional[int] = None
    error: Optional[str] = None


MODAL_LINKEDIN_JOB_VIDEO_URL = f"{MODAL_BASE_URL}-ingest-linkedin-job-video.modal.run"


@router.post(
    "/linkedin/job-video/ingest",
    response_model=LinkedInJobVideoResponse,
    summary="Extract job postings from LinkedIn job search video",
    description="Uploads a video recording of LinkedIn job search results, extracts frames, and uses GPT-4o vision to extract job postings"
)
async def ingest_linkedin_job_video(
    video: UploadFile = File(..., description="Video file (MP4, MOV, WebM) of LinkedIn job search"),
    search_query: Optional[str] = Form(None, description="LinkedIn search query used"),
    search_date: Optional[str] = Form(None, description="Date of search (YYYY-MM-DD)"),
    linkedin_search_url: Optional[str] = Form(None, description="Full LinkedIn search URL"),
) -> LinkedInJobVideoResponse:
    """
    Extract job postings from a video recording of LinkedIn job search results.

    1. Uploads video to Modal endpoint
    2. Extracts frames every 2 seconds (max 30 frames)
    3. Sends frames to GPT-4o vision for extraction
    4. Stores raw response + extracted jobs in database

    Returns job count and extraction metadata.
    """
    try:
        # Read video content
        video_content = await video.read()

        # Forward to Modal endpoint as multipart form data
        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"video": (video.filename, video_content, video.content_type or "video/mp4")}
            data = {}
            if search_query:
                data["search_query"] = search_query
            if search_date:
                data["search_date"] = search_date
            if linkedin_search_url:
                data["linkedin_search_url"] = linkedin_search_url

            response = await client.post(
                MODAL_LINKEDIN_JOB_VIDEO_URL,
                files=files,
                data=data,
            )

            if response.status_code != 200:
                return LinkedInJobVideoResponse(
                    success=False,
                    error=f"Modal endpoint returned {response.status_code}: {response.text}"
                )

            result = response.json()

            return LinkedInJobVideoResponse(
                success=result.get("success", False),
                raw_video_id=result.get("raw_video_id"),
                video_filename=result.get("video_filename"),
                video_duration_seconds=result.get("video_duration_seconds"),
                frames_extracted=result.get("frames_extracted"),
                jobs_extracted=result.get("jobs_extracted"),
                tokens_used=result.get("tokens_used"),
                error=result.get("error"),
            )

    except httpx.TimeoutException:
        return LinkedInJobVideoResponse(success=False, error="Request timed out - video processing may take up to 5 minutes")
    except Exception as e:
        return LinkedInJobVideoResponse(success=False, error=str(e))


# =============================================================================
# SalesNav Export to Clay Webhook
# =============================================================================

class SalesNavToClayResponse(BaseModel):
    success: bool
    total_rows: int = 0
    message: str = ""
    errors: List[str] = []


async def _send_rows_to_clay(
    rows: List[dict],
    webhook_url: str,
    export_title: Optional[str],
    export_timestamp: Optional[str],
    notes: Optional[str],
):
    """Background task to send rows to Clay webhook at 10 records/second."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, row in enumerate(rows):
            payload = {
                **row,
                "_export_title": export_title,
                "_export_timestamp": export_timestamp,
                "_notes": notes,
                "_row_index": i,
            }
            try:
                await client.post(webhook_url, json=payload)
            except Exception:
                pass  # Fire and forget
            await asyncio.sleep(0.1)  # 10 records/second


@router.post(
    "/salesnav/export/to-clay",
    response_model=SalesNavToClayResponse,
    summary="Send SalesNav export file to Clay webhook",
    description="Parses a TSV/CSV file and sends each row to Clay webhook in background at 10 records/second. Returns immediately."
)
async def salesnav_export_to_clay(
    file: UploadFile = File(..., description="TSV/CSV file from SalesNav export"),
    webhook_url: str = Form(..., description="Clay webhook URL to send records to"),
    export_title: Optional[str] = Form(None, description="Title for this export"),
    export_timestamp: Optional[str] = Form(None, description="Timestamp from SalesNav export"),
    notes: Optional[str] = Form(None, description="Additional notes"),
) -> SalesNavToClayResponse:
    """
    Send SalesNav export file to Clay webhook.

    1. Parses TSV/CSV file
    2. Kicks off background task to send rows to Clay at 10/second
    3. Returns immediately with row count

    Check Clay table to monitor progress.
    """
    try:
        # Read file content
        content = await file.read()
        text_content = content.decode('utf-8')

        # Detect delimiter (TSV vs CSV)
        first_line = text_content.split('\n')[0]
        delimiter = '\t' if '\t' in first_line else ','

        # Parse CSV/TSV
        reader = csv.DictReader(io.StringIO(text_content), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            return SalesNavToClayResponse(
                success=False,
                total_rows=0,
                errors=["No data rows found in file"]
            )

        total_rows = len(rows)

        # Fire off background task and return immediately
        asyncio.create_task(
            _send_rows_to_clay(rows, webhook_url, export_title, export_timestamp, notes)
        )

        return SalesNavToClayResponse(
            success=True,
            total_rows=total_rows,
            message=f"Sending {total_rows} rows to Clay in background. Check Clay table for progress.",
        )

    except UnicodeDecodeError:
        return SalesNavToClayResponse(
            success=False,
            errors=["File encoding error - ensure file is UTF-8 encoded"]
        )
    except Exception as e:
        return SalesNavToClayResponse(
            success=False,
            errors=[str(e)]
        )


# =============================================================================
# Case Study URLs: Send to Clay webhook
# =============================================================================


@router.post(
    "/case-study-urls/to-clay",
    summary="Send unsent case study URLs to Clay webhook (via Modal)",
    description="Proxies to Modal function that sends URLs at 10 records/second and marks each as sent_to_clay."
)
async def case_study_urls_to_clay(request: dict):
    """
    Proxy to Modal function: send_case_study_urls_to_clay.

    Body: { "webhook_url": "...", "batch_id": "..." (optional) }
    """
    modal_url = f"{MODAL_BASE_URL}-send-case-study-urls-to-clay.modal.run"
    async with httpx.AsyncClient(timeout=660.0) as client:
        resp = await client.post(modal_url, json=request)
        return resp.json()


# =============================================================================
# Client Leads: Send to Clay webhook
# =============================================================================


@router.post(
    "/client/leads/to-clay",
    summary="Send client leads to Clay webhook",
    description="Sends all leads for a client_domain to Clay at ~10 records/second."
)
async def send_client_leads_to_clay(request: dict):
    """
    Send leads for a client to Clay webhook for enrichment.

    Body: { "client_domain": "securitypalhq.com", "client_name": "SecurityPal AI" (optional) }

    Modal function: send_client_leads_to_clay
    Modal URL: https://bencrane--hq-master-data-ingest-send-client-leads-to-clay.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-send-client-leads-to-clay.modal.run"
    async with httpx.AsyncClient(timeout=660.0) as client:
        resp = await client.post(modal_url, json=request)
        return resp.json()


@router.post(
    "/companies/gemini/resolve-customer-domain/ingest",
    response_model=ResolveCustomerDomainResponse,
    summary="Resolve customer company domain using Gemini",
    description="Wrapper for Modal function: resolve_customer_domain"
)
async def resolve_customer_domain(request: ResolveCustomerDomainRequest) -> ResolveCustomerDomainResponse:
    """
    Use Gemini 3 Flash to resolve a customer company's domain from its name
    and the context of which company it is a customer of.

    Modal function: resolve_customer_domain
    Modal URL: https://bencrane--hq-master-data-ingest-resolve-customer-domain.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-resolve-customer-domain.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ResolveCustomerDomainResponse(**response.json())
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
    "/unresolved-customers/to-clay",
    summary="Send unresolved customer names to Clay webhook (via Modal)",
    description="Proxies to Modal function that sends customers without domains at 10 records/second."
)
async def unresolved_customers_to_clay(request: dict):
    """
    Proxy to Modal function: send_unresolved_customers_to_clay.

    Body: { "webhook_url": "...", "limit": 100 (optional) }
    """
    modal_url = f"{MODAL_BASE_URL}-send-unresolved-customer-74dc0a.modal.run"
    async with httpx.AsyncClient(timeout=660.0) as client:
        resp = await client.post(modal_url, json=request)
        return resp.json()


@router.post(
    "/companies/case-study-details/lookup",
    summary="Check if a case study URL has already been extracted",
    description="Returns whether extracted.case_study_details has a row for the given case_study_url."
)
async def lookup_case_study_details(request: dict):
    """
    Proxy to Modal function: lookup_case_study_details.

    Body: { "case_study_url": "https://..." }
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-case-study-details.modal.run"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(modal_url, json=request)
        return resp.json()


# =============================================================================
# Testing: Companies
# =============================================================================

class TestingCompanyRequest(BaseModel):
    name: str
    domain: str
    linkedin_url: Optional[str] = None


class TestingCompanyResponse(BaseModel):
    success: bool
    id: Optional[str] = None
    error: Optional[str] = None


@router.post(
    "/testing/companies",
    response_model=TestingCompanyResponse,
    summary="Add a company to testing.companies",
)
async def add_testing_company(request: TestingCompanyRequest) -> TestingCompanyResponse:
    """Insert a company into testing.companies table."""
    try:
        pool = await get_pool()
        result = await pool.fetchrow(
            """
            INSERT INTO testing.companies (name, domain, linkedin_url)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            request.name,
            request.domain,
            request.linkedin_url,
        )
        return TestingCompanyResponse(success=True, id=str(result["id"]))
    except Exception as e:
        return TestingCompanyResponse(success=False, error=str(e))


# =============================================================================
# CompanyEnrich.com Ingestion
# =============================================================================

class CompanyEnrichRequest(BaseModel):
    domain: str
    raw_payload: dict


class CompanyEnrichResponse(BaseModel):
    success: bool
    raw_id: Optional[str] = None
    extracted_id: Optional[str] = None
    funding_rounds_processed: Optional[int] = None
    error: Optional[str] = None


MODAL_COMPANYENRICH_URL = f"{MODAL_BASE_URL}-ingest-companyenrich.modal.run"


@router.post(
    "/companies/companyenrich/ingest",
    response_model=CompanyEnrichResponse,
    summary="Ingest company data from CompanyEnrich.com",
    description="Stores raw payload and extracts company firmographics + funding rounds"
)
async def ingest_companyenrich(request: CompanyEnrichRequest) -> CompanyEnrichResponse:
    """
    Ingest company enrichment data from CompanyEnrich.com.

    Stores raw payload in raw.companyenrich_payloads,
    extracts company data to extracted.companyenrich_company,
    and funding rounds to extracted.companyenrich_funding_rounds.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_COMPANYENRICH_URL,
                json=request.model_dump(),
            )

            if response.status_code != 200:
                return CompanyEnrichResponse(
                    success=False,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return CompanyEnrichResponse(
                success=result.get("success", False),
                raw_id=result.get("raw_id"),
                extracted_id=result.get("extracted_id"),
                funding_rounds_processed=result.get("funding_rounds_processed"),
                error=result.get("error"),
            )
    except Exception as e:
        return CompanyEnrichResponse(success=False, error=str(e))


# =============================================================================
# OpenAI Native - B2B/B2C Classification (DB Direct)
# =============================================================================

MODAL_CLASSIFY_B2B_B2C_URL = f"{MODAL_BASE_URL}-classify-b2b-b2c-openai-db-direct.modal.run"
WORKFLOW_SOURCE_B2B_B2C = "openai-native/b2b-b2c/classify/db-direct"
DEFAULT_MODEL_B2B_B2C = "gpt-4o"


class B2bB2cClassifyRequest(BaseModel):
    """Request for B2B/B2C classification."""
    client_domain: Optional[str] = None  # For batch processing HQ client records
    domains: Optional[List[str]] = None  # For direct domain list
    model: str = DEFAULT_MODEL_B2B_B2C


class B2bB2cClassifyResponse(BaseModel):
    """Response for B2B/B2C classification."""
    success: bool
    records_evaluated: int = 0
    fields_updated: int = 0
    records_already_classified: int = 0
    records_classified_by_ai: int = 0
    records_missing_description: int = 0
    errors: Optional[List[dict]] = None


@router.post(
    "/companies/openai-native/b2b-b2c/classify/db-direct",
    response_model=B2bB2cClassifyResponse,
    summary="Classify companies as B2B/B2C using OpenAI and write directly to DB",
    description="""
    Looks up domain in extracted table first. If not found, calls Modal function
    which uses OpenAI and writes to raw, extracted, and core tables.

    Modal URL: https://bencrane--hq-master-data-ingest-classify-b2b-b2c-openai-db-direct.modal.run
    """
)
async def classify_b2b_b2c_openai_db_direct(request: B2bB2cClassifyRequest) -> B2bB2cClassifyResponse:
    """
    Classify companies as B2B/B2C using OpenAI via Modal, writing directly to database.

    1. Lookup domain in extracted.company_classification_db_direct
    2. If found -> skip
    3. If not found -> call Modal function with company name, domain, description
    4. Modal writes to:
       - raw.company_classification_db_direct (request/response)
       - extracted.company_classification_db_direct (parsed results)
       - core.company_business_model (canonical booleans)
    """
    pool = get_pool()

    # Get domains to process
    domains_to_process = []

    if request.client_domain:
        # Get domains from HQ normalized data that have descriptions
        rows = await pool.fetch("""
            SELECT DISTINCT n.domain, n.company_name, d.description
            FROM hq.clients_normalized_crm_data n
            LEFT JOIN core.company_descriptions d ON n.domain = d.domain
            WHERE n.client_domain = $1
              AND n.domain IS NOT NULL
        """, request.client_domain)
        domains_to_process = [
            {"domain": r["domain"], "company_name": r["company_name"], "description": r["description"]}
            for r in rows
        ]
    elif request.domains:
        # Get company info for provided domains
        rows = await pool.fetch("""
            SELECT c.domain, c.name as company_name, d.description
            FROM core.companies c
            LEFT JOIN core.company_descriptions d ON c.domain = d.domain
            WHERE c.domain = ANY($1)
        """, request.domains)
        domains_to_process = [
            {"domain": r["domain"], "company_name": r["company_name"], "description": r["description"]}
            for r in rows
        ]
    else:
        return B2bB2cClassifyResponse(
            success=False,
            errors=[{"error": "Either client_domain or domains is required"}]
        )

    if not domains_to_process:
        return B2bB2cClassifyResponse(
            success=True,
            records_evaluated=0
        )

    # Check which domains are already classified
    domain_list = [d["domain"] for d in domains_to_process]
    existing = await pool.fetch("""
        SELECT domain FROM extracted.company_classification_db_direct
        WHERE domain = ANY($1)
    """, domain_list)
    already_classified = {r["domain"] for r in existing}

    # Process records
    records_evaluated = len(domains_to_process)
    fields_updated = 0
    records_already_classified = 0
    records_classified_by_ai = 0
    records_missing_description = 0
    errors = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for record in domains_to_process:
            domain = record["domain"]
            company_name = record["company_name"] or domain
            description = record["description"]

            try:
                # Skip if already classified
                if domain in already_classified:
                    records_already_classified += 1
                    continue

                # Skip if no description
                if not description:
                    records_missing_description += 1
                    continue

                # Call Modal function
                response = await client.post(
                    MODAL_CLASSIFY_B2B_B2C_URL,
                    json={
                        "domain": domain,
                        "company_name": company_name,
                        "description": description,
                        "model": request.model,
                        "workflow_source": WORKFLOW_SOURCE_B2B_B2C
                    }
                )

                if response.status_code != 200:
                    errors.append({"domain": domain, "error": f"Modal returned {response.status_code}"})
                    continue

                result = response.json()
                if result.get("success"):
                    fields_updated += 1
                    records_classified_by_ai += 1
                else:
                    errors.append({"domain": domain, "error": result.get("error", "Unknown error")})

            except Exception as e:
                errors.append({"domain": domain, "error": str(e)})

    return B2bB2cClassifyResponse(
        success=True,
        records_evaluated=records_evaluated,
        fields_updated=fields_updated,
        records_already_classified=records_already_classified,
        records_classified_by_ai=records_classified_by_ai,
        records_missing_description=records_missing_description,
        errors=errors if errors else None
    )


# =============================================================================
# Adyntel Native - LinkedIn Ads (DB Direct)
# =============================================================================

MODAL_LINKEDIN_ADS_DB_DIRECT_URL = f"{MODAL_BASE_URL}-ingest-linkedin-ads-db-direct.modal.run"
WORKFLOW_SOURCE_LINKEDIN_ADS = "adyntel-native/linkedin-ads/ingest/db-direct"


class LinkedInAdsDbDirectRequest(BaseModel):
    """Request for LinkedIn ads ingestion (db-direct)."""
    domain: str
    linkedin_ads_payload: dict
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class LinkedInAdsDbDirectResponse(BaseModel):
    """Response for LinkedIn ads ingestion (db-direct)."""
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/adyntel-native/linkedin-ads/ingest/db-direct",
    response_model=LinkedInAdsDbDirectResponse,
    summary="Ingest LinkedIn ads from Adyntel and write directly to DB",
    description="""
    Receives LinkedIn ads payload from UI/Prefect (which called Adyntel),
    writes to raw, extracted, and core tables.

    TTL logic:
    - ttl_days=None: skip if domain already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if last_checked_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-ingest-linkedin-ads-db-direct.modal.run
    """
)
async def ingest_linkedin_ads_db_direct(request: LinkedInAdsDbDirectRequest) -> LinkedInAdsDbDirectResponse:
    """
    Ingest LinkedIn ads data from Adyntel, writing directly to database.

    1. Check TTL to decide if should process
    2. If should process, call Modal function
    3. Modal writes to raw, extracted, core tables
    """
    pool = get_pool()
    domain = request.domain

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists (any)
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_linkedin_ads
            WHERE domain = $1
        """, domain)
        if existing:
            return LinkedInAdsDbDirectResponse(
                success=True,
                domain=domain,
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_linkedin_ads
            WHERE domain = $1
        """, domain)
        if existing and existing["last_checked_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["last_checked_at"] > cutoff:
                return LinkedInAdsDbDirectResponse(
                    success=True,
                    domain=domain,
                    skipped_ttl=True
                )
    # ttl_days=0 means always refresh, so no skip check

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_LINKEDIN_ADS_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "linkedin_ads_payload": request.linkedin_ads_payload,
                    "workflow_source": WORKFLOW_SOURCE_LINKEDIN_ADS
                }
            )

            if response.status_code != 200:
                return LinkedInAdsDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return LinkedInAdsDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                raw_payload_id=result.get("raw_payload_id"),
                ads_extracted=result.get("ads_extracted"),
                total_ads=result.get("total_ads"),
                is_running_ads=result.get("is_running_ads"),
                error=result.get("error")
            )
    except Exception as e:
        return LinkedInAdsDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Adyntel Native - Meta Ads (DB Direct)
# =============================================================================

MODAL_META_ADS_DB_DIRECT_URL = f"{MODAL_BASE_URL}-ingest-meta-ads-db-direct.modal.run"
WORKFLOW_SOURCE_META_ADS = "adyntel-native/meta-ads/ingest/db-direct"


class MetaAdsDbDirectRequest(BaseModel):
    """Request for Meta ads ingestion (db-direct)."""
    domain: str
    meta_ads_payload: dict
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class MetaAdsDbDirectResponse(BaseModel):
    """Response for Meta ads ingestion (db-direct)."""
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    platforms: Optional[List[str]] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/adyntel-native/meta-ads/ingest/db-direct",
    response_model=MetaAdsDbDirectResponse,
    summary="Ingest Meta ads from Adyntel and write directly to DB",
    description="""
    Receives Meta ads payload from UI/Prefect (which called Adyntel),
    writes to raw, extracted, and core tables.

    TTL logic:
    - ttl_days=None: skip if domain already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if last_checked_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-ingest-meta-ads-db-direct.modal.run
    """
)
async def ingest_meta_ads_db_direct(request: MetaAdsDbDirectRequest) -> MetaAdsDbDirectResponse:
    """
    Ingest Meta ads data from Adyntel, writing directly to database.

    1. Check TTL to decide if should process
    2. If should process, call Modal function
    3. Modal writes to raw, extracted, core tables
    """
    pool = get_pool()
    domain = request.domain

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists (any)
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_meta_ads
            WHERE domain = $1
        """, domain)
        if existing:
            return MetaAdsDbDirectResponse(
                success=True,
                domain=domain,
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_meta_ads
            WHERE domain = $1
        """, domain)
        if existing and existing["last_checked_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["last_checked_at"] > cutoff:
                return MetaAdsDbDirectResponse(
                    success=True,
                    domain=domain,
                    skipped_ttl=True
                )
    # ttl_days=0 means always refresh, so no skip check

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_META_ADS_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "meta_ads_payload": request.meta_ads_payload,
                    "workflow_source": WORKFLOW_SOURCE_META_ADS
                }
            )

            if response.status_code != 200:
                return MetaAdsDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return MetaAdsDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                raw_payload_id=result.get("raw_payload_id"),
                ads_extracted=result.get("ads_extracted"),
                total_ads=result.get("total_ads"),
                is_running_ads=result.get("is_running_ads"),
                platforms=result.get("platforms"),
                error=result.get("error")
            )
    except Exception as e:
        return MetaAdsDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Adyntel Native - Google Ads (DB Direct)
# =============================================================================

MODAL_GOOGLE_ADS_DB_DIRECT_URL = f"{MODAL_BASE_URL}-ingest-google-ads-db-direct.modal.run"
WORKFLOW_SOURCE_GOOGLE_ADS = "adyntel-native/google-ads/ingest/db-direct"


class GoogleAdsDbDirectRequest(BaseModel):
    """Request for Google ads ingestion (db-direct)."""
    domain: str
    google_ads_payload: dict
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class GoogleAdsDbDirectResponse(BaseModel):
    """Response for Google ads ingestion (db-direct)."""
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    ads_extracted: Optional[int] = None
    total_ads: Optional[int] = None
    is_running_ads: Optional[bool] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/adyntel-native/google-ads/ingest/db-direct",
    response_model=GoogleAdsDbDirectResponse,
    summary="Ingest Google ads from Adyntel and write directly to DB",
    description="""
    Receives Google ads payload from UI/Prefect (which called Adyntel),
    writes to raw, extracted, and core tables.

    TTL logic:
    - ttl_days=None: skip if domain already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if last_checked_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-ingest-google-ads-db-direct.modal.run
    """
)
async def ingest_google_ads_db_direct(request: GoogleAdsDbDirectRequest) -> GoogleAdsDbDirectResponse:
    """
    Ingest Google ads data from Adyntel, writing directly to database.

    1. Check TTL to decide if should process
    2. If should process, call Modal function
    3. Modal writes to raw, extracted, core tables
    """
    pool = get_pool()
    domain = request.domain

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists (any)
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_google_ads
            WHERE domain = $1
        """, domain)
        if existing:
            return GoogleAdsDbDirectResponse(
                success=True,
                domain=domain,
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, last_checked_at
            FROM core.company_google_ads
            WHERE domain = $1
        """, domain)
        if existing and existing["last_checked_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["last_checked_at"] > cutoff:
                return GoogleAdsDbDirectResponse(
                    success=True,
                    domain=domain,
                    skipped_ttl=True
                )
    # ttl_days=0 means always refresh, so no skip check

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_GOOGLE_ADS_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "google_ads_payload": request.google_ads_payload,
                    "workflow_source": WORKFLOW_SOURCE_GOOGLE_ADS
                }
            )

            if response.status_code != 200:
                return GoogleAdsDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return GoogleAdsDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                raw_payload_id=result.get("raw_payload_id"),
                ads_extracted=result.get("ads_extracted"),
                total_ads=result.get("total_ads"),
                is_running_ads=result.get("is_running_ads"),
                error=result.get("error")
            )
    except Exception as e:
        return GoogleAdsDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel Native - Company Description (DB Direct)
# =============================================================================

MODAL_DESCRIPTION_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-description-db-direct.modal.run"
WORKFLOW_SOURCE_DESCRIPTION = "parallel-native/description/infer/db-direct"


class DescriptionDbDirectRequest(BaseModel):
    """Request for company description inference (db-direct)."""
    domain: str
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class DescriptionDbDirectBatchRequest(BaseModel):
    """Batch request for company description inference (db-direct)."""
    client_domain: Optional[str] = None  # For batch processing HQ client records
    domains: Optional[List[str]] = None  # For direct domain list
    ttl_days: Optional[int] = None


class DescriptionDbDirectResponse(BaseModel):
    """Response for company description inference (db-direct)."""
    success: bool
    domain: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


class DescriptionDbDirectBatchResponse(BaseModel):
    """Batch response for company description inference (db-direct)."""
    success: bool
    records_evaluated: int = 0
    fields_updated: int = 0
    records_already_had_value: int = 0
    records_inferred: int = 0
    errors: Optional[List[dict]] = None


@router.post(
    "/companies/parallel-native/description/infer/db-direct",
    response_model=DescriptionDbDirectResponse,
    summary="Infer company description using Parallel AI and write directly to DB",
    description="""
    Checks core.company_descriptions first. If not found (or TTL expired),
    calls Parallel AI Task Enrichment API to get description.

    TTL logic:
    - ttl_days=None: skip if description already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if updated_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-infer-description-db-direct.modal.run
    """
)
async def infer_description_db_direct(request: DescriptionDbDirectRequest) -> DescriptionDbDirectResponse:
    """
    Infer company description using Parallel AI, writing directly to database.
    """
    pool = get_pool()
    domain = request.domain

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists with description
        existing = await pool.fetchrow("""
            SELECT domain, description, updated_at
            FROM core.company_descriptions
            WHERE domain = $1 AND description IS NOT NULL
        """, domain)
        if existing:
            return DescriptionDbDirectResponse(
                success=True,
                domain=domain,
                description=existing["description"],
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, description, updated_at
            FROM core.company_descriptions
            WHERE domain = $1 AND description IS NOT NULL
        """, domain)
        if existing and existing["updated_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["updated_at"] > cutoff:
                return DescriptionDbDirectResponse(
                    success=True,
                    domain=domain,
                    description=existing["description"],
                    skipped_ttl=True
                )

    # Get company info if not provided
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url

    if not company_name:
        company_row = await pool.fetchrow("""
            SELECT name, linkedin_url FROM core.companies WHERE domain = $1
        """, domain)
        if company_row:
            company_name = company_row["name"]
            company_linkedin_url = company_linkedin_url or company_row["linkedin_url"]

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_DESCRIPTION_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": company_name or domain,
                    "company_linkedin_url": company_linkedin_url,
                    "workflow_source": WORKFLOW_SOURCE_DESCRIPTION
                }
            )

            if response.status_code != 200:
                return DescriptionDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return DescriptionDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                description=result.get("description"),
                tagline=result.get("tagline"),
                error=result.get("error")
            )
    except Exception as e:
        return DescriptionDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


@router.post(
    "/companies/parallel-native/description/infer/db-direct/batch",
    response_model=DescriptionDbDirectBatchResponse,
    summary="Batch infer company descriptions using Parallel AI",
    description="Process multiple domains for description inference."
)
async def infer_description_db_direct_batch(request: DescriptionDbDirectBatchRequest) -> DescriptionDbDirectBatchResponse:
    """
    Batch infer company descriptions using Parallel AI.
    """
    pool = get_pool()

    # Get domains to process
    domains_to_process = []

    if request.client_domain:
        rows = await pool.fetch("""
            SELECT DISTINCT n.domain, n.company_name, n.company_linkedin_url
            FROM hq.clients_normalized_crm_data n
            WHERE n.client_domain = $1
              AND n.domain IS NOT NULL
        """, request.client_domain)
        domains_to_process = [
            {"domain": r["domain"], "company_name": r["company_name"], "company_linkedin_url": r["company_linkedin_url"]}
            for r in rows
        ]
    elif request.domains:
        rows = await pool.fetch("""
            SELECT domain, name as company_name, linkedin_url as company_linkedin_url
            FROM core.companies
            WHERE domain = ANY($1)
        """, request.domains)
        domain_map = {r["domain"]: r for r in rows}
        domains_to_process = [
            {"domain": d, "company_name": domain_map.get(d, {}).get("company_name"), "company_linkedin_url": domain_map.get(d, {}).get("company_linkedin_url")}
            for d in request.domains
        ]
    else:
        return DescriptionDbDirectBatchResponse(
            success=False,
            errors=[{"error": "Either client_domain or domains is required"}]
        )

    if not domains_to_process:
        return DescriptionDbDirectBatchResponse(success=True, records_evaluated=0)

    # Check which domains already have descriptions
    domain_list = [d["domain"] for d in domains_to_process]

    if request.ttl_days is None:
        existing = await pool.fetch("""
            SELECT domain FROM core.company_descriptions
            WHERE domain = ANY($1) AND description IS NOT NULL
        """, domain_list)
        already_have_description = {r["domain"] for r in existing}
    elif request.ttl_days > 0:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
        existing = await pool.fetch("""
            SELECT domain FROM core.company_descriptions
            WHERE domain = ANY($1) AND description IS NOT NULL AND updated_at > $2
        """, domain_list, cutoff)
        already_have_description = {r["domain"] for r in existing}
    else:
        already_have_description = set()

    # Process records
    records_evaluated = len(domains_to_process)
    fields_updated = 0
    records_already_had_value = 0
    records_inferred = 0
    errors = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for record in domains_to_process:
            domain = record["domain"]
            company_name = record["company_name"] or domain
            company_linkedin_url = record["company_linkedin_url"]

            try:
                if domain in already_have_description:
                    records_already_had_value += 1
                    continue

                response = await client.post(
                    MODAL_DESCRIPTION_DB_DIRECT_URL,
                    json={
                        "domain": domain,
                        "company_name": company_name,
                        "company_linkedin_url": company_linkedin_url,
                        "workflow_source": WORKFLOW_SOURCE_DESCRIPTION
                    }
                )

                if response.status_code != 200:
                    errors.append({"domain": domain, "error": f"Modal returned {response.status_code}"})
                    continue

                result = response.json()
                if result.get("success"):
                    fields_updated += 1
                    records_inferred += 1
                else:
                    errors.append({"domain": domain, "error": result.get("error", "Unknown error")})

            except Exception as e:
                errors.append({"domain": domain, "error": str(e)})

    return DescriptionDbDirectBatchResponse(
        success=True,
        records_evaluated=records_evaluated,
        fields_updated=fields_updated,
        records_already_had_value=records_already_had_value,
        records_inferred=records_inferred,
        errors=errors if errors else None
    )


# =============================================================================
# G2 URL Inference (Parallel AI Search API) - DB Direct
# =============================================================================

MODAL_G2_URL_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-g2-url-db-direct.modal.run"
WORKFLOW_SOURCE_G2_URL = "parallel-native/g2-url/infer/db-direct"


class G2UrlDbDirectRequest(BaseModel):
    """Request for G2 URL inference (db-direct)."""
    domain: str
    company_name: str
    cleaned_company_name: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=days


class G2UrlDbDirectResponse(BaseModel):
    """Response for G2 URL inference (db-direct)."""
    success: bool
    domain: str
    g2_url: Optional[str] = None
    error: Optional[str] = None


class G2UrlDbDirectBatchRequest(BaseModel):
    """Batch request for G2 URL inference (db-direct)."""
    domains: Optional[List[str]] = None
    client_domain: Optional[str] = None
    ttl_days: Optional[int] = None


class G2UrlDbDirectBatchResponse(BaseModel):
    """Batch response for G2 URL inference (db-direct)."""
    success: bool
    records_evaluated: int = 0
    fields_updated: int = 0
    records_already_had_value: int = 0
    errors: Optional[List[dict]] = None


@router.post(
    "/companies/parallel-native/g2-url/infer/db-direct",
    response_model=G2UrlDbDirectResponse,
    summary="Infer G2 URL using Parallel AI Search",
    description="""
    Find G2 reviews page URL using Parallel AI Search API.

    Modal URL: https://bencrane--hq-master-data-ingest-infer-g2-url-db-direct.modal.run

    Workflow: parallel-native/g2-url/infer/db-direct

    TTL Logic:
    - ttl_days=None (default): Skip if g2_url exists
    - ttl_days=0: Always refresh
    - ttl_days=N: Refresh if older than N days
    """
)
async def infer_g2_url_db_direct(request: G2UrlDbDirectRequest) -> G2UrlDbDirectResponse:
    """
    Infer G2 URL using Parallel AI Search API.
    """
    pool = get_pool()
    domain = request.domain.lower().strip()

    # Check TTL logic
    if request.ttl_days is None:
        existing = await pool.fetchrow("""
            SELECT g2_url FROM core.company_g2
            WHERE domain = $1 AND g2_url IS NOT NULL
        """, domain)
        if existing:
            return G2UrlDbDirectResponse(
                success=True,
                domain=domain,
                g2_url=existing["g2_url"]
            )
    elif request.ttl_days > 0:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
        existing = await pool.fetchrow("""
            SELECT g2_url FROM core.company_g2
            WHERE domain = $1 AND g2_url IS NOT NULL AND updated_at > $2
        """, domain, cutoff)
        if existing:
            return G2UrlDbDirectResponse(
                success=True,
                domain=domain,
                g2_url=existing["g2_url"]
            )

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Use cleaned_company_name if provided, otherwise company_name
            search_name = request.cleaned_company_name if request.cleaned_company_name else request.company_name

            response = await client.post(
                MODAL_G2_URL_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": request.company_name,
                    "cleaned_company_name": request.cleaned_company_name,
                    "workflow_source": WORKFLOW_SOURCE_G2_URL
                }
            )

            if response.status_code != 200:
                return G2UrlDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return G2UrlDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                g2_url=result.get("g2_url"),
                error=result.get("error")
            )

    except Exception as e:
        return G2UrlDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


@router.post(
    "/companies/parallel-native/g2-url/infer/db-direct/batch",
    response_model=G2UrlDbDirectBatchResponse,
    summary="Batch infer G2 URLs using Parallel AI Search",
    description="Process multiple domains for G2 URL inference."
)
async def infer_g2_url_db_direct_batch(request: G2UrlDbDirectBatchRequest) -> G2UrlDbDirectBatchResponse:
    """
    Batch infer G2 URLs using Parallel AI Search API.
    """
    pool = get_pool()

    # Get domains to process
    domains_to_process = []

    if request.client_domain:
        rows = await pool.fetch("""
            SELECT DISTINCT n.domain, n.company_name, n.cleaned_company_name
            FROM hq.clients_normalized_crm_data n
            WHERE n.client_domain = $1
              AND n.domain IS NOT NULL
        """, request.client_domain)
        domains_to_process = [
            {"domain": r["domain"], "company_name": r["company_name"], "cleaned_company_name": r.get("cleaned_company_name")}
            for r in rows
        ]
    elif request.domains:
        rows = await pool.fetch("""
            SELECT domain, name as company_name
            FROM core.companies
            WHERE domain = ANY($1)
        """, request.domains)
        domain_map = {r["domain"]: r for r in rows}
        domains_to_process = [
            {"domain": d, "company_name": domain_map.get(d, {}).get("company_name") or d, "cleaned_company_name": None}
            for d in request.domains
        ]
    else:
        return G2UrlDbDirectBatchResponse(
            success=False,
            errors=[{"error": "Either client_domain or domains is required"}]
        )

    if not domains_to_process:
        return G2UrlDbDirectBatchResponse(success=True, records_evaluated=0)

    # Check which domains already have G2 URLs
    domain_list = [d["domain"] for d in domains_to_process]

    if request.ttl_days is None:
        existing = await pool.fetch("""
            SELECT domain FROM core.company_g2
            WHERE domain = ANY($1) AND g2_url IS NOT NULL
        """, domain_list)
        already_have_g2 = {r["domain"] for r in existing}
    elif request.ttl_days > 0:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
        existing = await pool.fetch("""
            SELECT domain FROM core.company_g2
            WHERE domain = ANY($1) AND g2_url IS NOT NULL AND updated_at > $2
        """, domain_list, cutoff)
        already_have_g2 = {r["domain"] for r in existing}
    else:
        already_have_g2 = set()

    # Process records
    records_evaluated = len(domains_to_process)
    fields_updated = 0
    records_already_had_value = 0
    errors = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for record in domains_to_process:
            domain = record["domain"]
            company_name = record["company_name"] or domain
            cleaned_company_name = record.get("cleaned_company_name")

            try:
                if domain in already_have_g2:
                    records_already_had_value += 1
                    continue

                response = await client.post(
                    MODAL_G2_URL_DB_DIRECT_URL,
                    json={
                        "domain": domain,
                        "company_name": company_name,
                        "cleaned_company_name": cleaned_company_name,
                        "workflow_source": WORKFLOW_SOURCE_G2_URL
                    }
                )

                if response.status_code != 200:
                    errors.append({"domain": domain, "error": f"Modal returned {response.status_code}"})
                    continue

                result = response.json()
                if result.get("success"):
                    fields_updated += 1
                else:
                    errors.append({"domain": domain, "error": result.get("error", "Unknown error")})

            except Exception as e:
                errors.append({"domain": domain, "error": str(e)})

    return G2UrlDbDirectBatchResponse(
        success=True,
        records_evaluated=records_evaluated,
        fields_updated=fields_updated,
        records_already_had_value=records_already_had_value,
        errors=errors if errors else None
    )


# =============================================================================
# G2 Insights Extraction (Gemini) - DB Direct
# =============================================================================

MODAL_G2_INSIGHTS_DB_DIRECT_URL = f"{MODAL_BASE_URL}-extract-g2-insights-db-direct.modal.run"
WORKFLOW_SOURCE_G2_INSIGHTS = "gemini-native/g2-insights/extract/db-direct"


class G2InsightsDbDirectRequest(BaseModel):
    """Request for G2 insights extraction (db-direct)."""
    domain: str
    g2_url: str


class G2InsightsDbDirectResponse(BaseModel):
    """Response for G2 insights extraction (db-direct)."""
    success: bool
    domain: str
    g2_url: Optional[str] = None
    overall_rating: Optional[str] = None
    total_reviews: Optional[str] = None
    top_complaints: Optional[List[str]] = None
    top_praise: Optional[List[str]] = None
    negative_quotes: Optional[List[str]] = None
    error: Optional[str] = None


@router.post(
    "/companies/gemini-native/g2-insights/extract/db-direct",
    response_model=G2InsightsDbDirectResponse,
    summary="Extract G2 review insights using Gemini",
    description="""
    Extract insights from G2 reviews page using Gemini.

    Modal URL: https://bencrane--hq-master-data-ingest-extract-g2-insights-db-direct.modal.run

    Workflow: gemini-native/g2-insights/extract/db-direct

    Extracts:
    - Overall rating
    - Total reviews
    - Top complaints/pain points
    - Top praise points
    - Negative quotes
    """
)
async def extract_g2_insights_db_direct(request: G2InsightsDbDirectRequest) -> G2InsightsDbDirectResponse:
    """
    Extract G2 review insights using Gemini.
    """
    domain = request.domain.lower().strip()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_G2_INSIGHTS_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "g2_url": request.g2_url,
                    "workflow_source": WORKFLOW_SOURCE_G2_INSIGHTS
                }
            )

            if response.status_code != 200:
                return G2InsightsDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return G2InsightsDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                g2_url=result.get("g2_url"),
                overall_rating=result.get("overall_rating"),
                total_reviews=result.get("total_reviews"),
                top_complaints=result.get("top_complaints"),
                top_praise=result.get("top_praise"),
                negative_quotes=result.get("negative_quotes"),
                error=result.get("error")
            )

    except Exception as e:
        return G2InsightsDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel Native - Company Revenue (DB Direct)
# =============================================================================

MODAL_REVENUE_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-revenue-db-direct.modal.run"
WORKFLOW_SOURCE_REVENUE = "parallel-native/revenue/infer/db-direct"


class RevenueDbDirectRequest(BaseModel):
    """Request for company revenue inference (db-direct)."""
    domain: str
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class RevenueDbDirectResponse(BaseModel):
    """Response for company revenue inference (db-direct)."""
    success: bool
    domain: Optional[str] = None
    annual_revenue_usd: Optional[int] = None
    revenue_range: Optional[str] = None
    confidence: Optional[str] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/parallel-native/revenue/infer/db-direct",
    response_model=RevenueDbDirectResponse,
    summary="Infer company annual revenue using Parallel AI and write directly to DB",
    description="""
    Checks core.company_revenue first. If not found (or TTL expired),
    calls Parallel AI Task Enrichment API to get revenue estimate.

    TTL logic:
    - ttl_days=None: skip if revenue already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if updated_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-infer-revenue-db-direct.modal.run
    """
)
async def infer_revenue_db_direct(request: RevenueDbDirectRequest) -> RevenueDbDirectResponse:
    """
    Infer company annual revenue using Parallel AI, writing directly to database.
    """
    pool = get_pool()
    domain = request.domain.lower().strip()

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists with revenue
        existing = await pool.fetchrow("""
            SELECT domain, raw_revenue_amount, raw_revenue_range, updated_at
            FROM core.company_revenue
            WHERE domain = $1 AND (raw_revenue_amount IS NOT NULL OR raw_revenue_range IS NOT NULL)
        """, domain)
        if existing:
            return RevenueDbDirectResponse(
                success=True,
                domain=domain,
                annual_revenue_usd=existing["raw_revenue_amount"],
                revenue_range=existing["raw_revenue_range"],
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, raw_revenue_amount, raw_revenue_range, updated_at
            FROM core.company_revenue
            WHERE domain = $1 AND (raw_revenue_amount IS NOT NULL OR raw_revenue_range IS NOT NULL)
        """, domain)
        if existing and existing["updated_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["updated_at"] > cutoff:
                return RevenueDbDirectResponse(
                    success=True,
                    domain=domain,
                    annual_revenue_usd=existing["raw_revenue_amount"],
                    revenue_range=existing["raw_revenue_range"],
                    skipped_ttl=True
                )

    # Get company info if not provided
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url

    if not company_name:
        company_row = await pool.fetchrow("""
            SELECT name, linkedin_url FROM core.companies WHERE domain = $1
        """, domain)
        if company_row:
            company_name = company_row["name"]
            company_linkedin_url = company_linkedin_url or company_row["linkedin_url"]

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_REVENUE_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": company_name or domain,
                    "company_linkedin_url": company_linkedin_url,
                    "workflow_source": WORKFLOW_SOURCE_REVENUE
                }
            )

            if response.status_code != 200:
                return RevenueDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return RevenueDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                annual_revenue_usd=result.get("annual_revenue_usd"),
                revenue_range=result.get("revenue_range"),
                confidence=result.get("confidence"),
                error=result.get("error")
            )
    except Exception as e:
        return RevenueDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel Native - Company Funding (DB Direct)
# =============================================================================

MODAL_FUNDING_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-funding-db-direct.modal.run"
WORKFLOW_SOURCE_FUNDING = "parallel-native/funding/infer/db-direct"


class FundingDbDirectRequest(BaseModel):
    """Request for company funding inference (db-direct)."""
    domain: str
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class FundingDbDirectResponse(BaseModel):
    """Response for company funding inference (db-direct)."""
    success: bool
    domain: Optional[str] = None
    total_funding_usd: Optional[int] = None
    funding_range: Optional[str] = None
    confidence: Optional[str] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/parallel-native/funding/infer/db-direct",
    response_model=FundingDbDirectResponse,
    summary="Infer company total funding raised using Parallel AI and write directly to DB",
    description="""
    Checks core.company_funding first. If not found (or TTL expired),
    calls Parallel AI Task Enrichment API to get funding estimate.

    TTL logic:
    - ttl_days=None: skip if funding already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if updated_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-infer-funding-db-direct.modal.run
    """
)
async def infer_funding_db_direct(request: FundingDbDirectRequest) -> FundingDbDirectResponse:
    """
    Infer company total funding raised using Parallel AI, writing directly to database.
    """
    pool = get_pool()
    domain = request.domain.lower().strip()

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists with funding
        existing = await pool.fetchrow("""
            SELECT domain, raw_funding_amount, raw_funding_range, updated_at
            FROM core.company_funding
            WHERE domain = $1 AND (raw_funding_amount IS NOT NULL OR raw_funding_range IS NOT NULL)
        """, domain)
        if existing:
            return FundingDbDirectResponse(
                success=True,
                domain=domain,
                total_funding_usd=existing["raw_funding_amount"],
                funding_range=existing["raw_funding_range"],
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, raw_funding_amount, raw_funding_range, updated_at
            FROM core.company_funding
            WHERE domain = $1 AND (raw_funding_amount IS NOT NULL OR raw_funding_range IS NOT NULL)
        """, domain)
        if existing and existing["updated_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["updated_at"] > cutoff:
                return FundingDbDirectResponse(
                    success=True,
                    domain=domain,
                    total_funding_usd=existing["raw_funding_amount"],
                    funding_range=existing["raw_funding_range"],
                    skipped_ttl=True
                )

    # Get company info if not provided
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url

    if not company_name:
        company_row = await pool.fetchrow("""
            SELECT name, linkedin_url FROM core.companies WHERE domain = $1
        """, domain)
        if company_row:
            company_name = company_row["name"]
            company_linkedin_url = company_linkedin_url or company_row["linkedin_url"]

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_FUNDING_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": company_name or domain,
                    "company_linkedin_url": company_linkedin_url,
                    "workflow_source": WORKFLOW_SOURCE_FUNDING
                }
            )

            if response.status_code != 200:
                return FundingDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return FundingDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                total_funding_usd=result.get("total_funding_usd"),
                funding_range=result.get("funding_range"),
                confidence=result.get("confidence"),
                error=result.get("error")
            )
    except Exception as e:
        return FundingDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel Native - Company Employees (DB Direct)
# =============================================================================

MODAL_EMPLOYEES_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-employees-db-direct.modal.run"
WORKFLOW_SOURCE_EMPLOYEES = "parallel-native/employees/infer/db-direct"


class EmployeesDbDirectRequest(BaseModel):
    """Request for company employee count inference (db-direct)."""
    domain: str
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class EmployeesDbDirectResponse(BaseModel):
    """Response for company employee count inference (db-direct)."""
    success: bool
    domain: Optional[str] = None
    employee_count: Optional[int] = None
    employee_range: Optional[str] = None
    confidence: Optional[str] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/parallel-native/employees/infer/db-direct",
    response_model=EmployeesDbDirectResponse,
    summary="Infer company employee count using Parallel AI and write directly to DB",
    description="""
    Checks core.company_employee_range first. If not found (or TTL expired),
    calls Parallel AI Task Enrichment API to get employee count estimate.

    TTL logic:
    - ttl_days=None: skip if employee data already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if updated_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-infer-employees-db-direct.modal.run
    """
)
async def infer_employees_db_direct(request: EmployeesDbDirectRequest) -> EmployeesDbDirectResponse:
    """
    Infer company employee count using Parallel AI, writing directly to database.
    """
    pool = get_pool()
    domain = request.domain.lower().strip()

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists with employee_range
        existing = await pool.fetchrow("""
            SELECT domain, employee_range, updated_at
            FROM core.company_employee_range
            WHERE domain = $1 AND employee_range IS NOT NULL
        """, domain)
        if existing:
            return EmployeesDbDirectResponse(
                success=True,
                domain=domain,
                employee_range=existing["employee_range"],
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, employee_range, updated_at
            FROM core.company_employee_range
            WHERE domain = $1 AND employee_range IS NOT NULL
        """, domain)
        if existing and existing["updated_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["updated_at"] > cutoff:
                return EmployeesDbDirectResponse(
                    success=True,
                    domain=domain,
                    employee_range=existing["employee_range"],
                    skipped_ttl=True
                )

    # Get company info if not provided
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url

    if not company_name:
        company_row = await pool.fetchrow("""
            SELECT name, linkedin_url FROM core.companies WHERE domain = $1
        """, domain)
        if company_row:
            company_name = company_row["name"]
            company_linkedin_url = company_linkedin_url or company_row["linkedin_url"]

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_EMPLOYEES_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": company_name or domain,
                    "company_linkedin_url": company_linkedin_url,
                    "workflow_source": WORKFLOW_SOURCE_EMPLOYEES
                }
            )

            if response.status_code != 200:
                return EmployeesDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return EmployeesDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                employee_count=result.get("employee_count"),
                employee_range=result.get("employee_range"),
                confidence=result.get("confidence"),
                error=result.get("error")
            )
    except Exception as e:
        return EmployeesDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel Native - Company Last Funding Date (DB Direct)
# =============================================================================

MODAL_LAST_FUNDING_DATE_DB_DIRECT_URL = f"{MODAL_BASE_URL}-infer-last-funding-date--d7eaa1.modal.run"
WORKFLOW_SOURCE_LAST_FUNDING_DATE = "parallel-native/last-funding-date/infer/db-direct"


class LastFundingDateDbDirectRequest(BaseModel):
    """Request for company last funding date inference (db-direct)."""
    domain: str
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    ttl_days: Optional[int] = None  # None=skip if exists, 0=always refresh, N=refresh if older than N days


class LastFundingDateDbDirectResponse(BaseModel):
    """Response for company last funding date inference (db-direct)."""
    success: bool
    domain: Optional[str] = None
    last_funding_date: Optional[str] = None
    funding_type: Optional[str] = None
    confidence: Optional[str] = None
    skipped_ttl: bool = False
    error: Optional[str] = None


@router.post(
    "/companies/parallel-native/last-funding-date/infer/db-direct",
    response_model=LastFundingDateDbDirectResponse,
    summary="Infer company last funding date using Parallel AI and write directly to DB",
    description="""
    Checks core.company_funding_rounds first. If not found (or TTL expired),
    calls Parallel AI Task Enrichment API to get last funding date.

    TTL logic:
    - ttl_days=None: skip if funding date already exists (default)
    - ttl_days=0: always refresh
    - ttl_days=N: refresh if updated_at older than N days

    Modal URL: https://bencrane--hq-master-data-ingest-infer-last-funding-date-db-direct.modal.run
    """
)
async def infer_last_funding_date_db_direct(request: LastFundingDateDbDirectRequest) -> LastFundingDateDbDirectResponse:
    """
    Infer company last funding date using Parallel AI, writing directly to database.
    """
    pool = get_pool()
    domain = request.domain.lower().strip()

    # Check TTL logic
    if request.ttl_days is None:
        # Skip if exists with funding_date
        existing = await pool.fetchrow("""
            SELECT domain, funding_date, funding_type, updated_at
            FROM core.company_funding_rounds
            WHERE domain = $1 AND funding_date IS NOT NULL
        """, domain)
        if existing:
            funding_date_str = None
            if existing["funding_date"]:
                funding_date_str = existing["funding_date"].strftime("%Y-%m-%d")
            return LastFundingDateDbDirectResponse(
                success=True,
                domain=domain,
                last_funding_date=funding_date_str,
                funding_type=existing["funding_type"],
                skipped_ttl=True
            )
    elif request.ttl_days > 0:
        # Check if older than TTL
        from datetime import datetime, timedelta, timezone
        existing = await pool.fetchrow("""
            SELECT domain, funding_date, funding_type, updated_at
            FROM core.company_funding_rounds
            WHERE domain = $1 AND funding_date IS NOT NULL
        """, domain)
        if existing and existing["updated_at"]:
            cutoff = datetime.now(timezone.utc) - timedelta(days=request.ttl_days)
            if existing["updated_at"] > cutoff:
                funding_date_str = None
                if existing["funding_date"]:
                    funding_date_str = existing["funding_date"].strftime("%Y-%m-%d")
                return LastFundingDateDbDirectResponse(
                    success=True,
                    domain=domain,
                    last_funding_date=funding_date_str,
                    funding_type=existing["funding_type"],
                    skipped_ttl=True
                )

    # Get company info if not provided
    company_name = request.company_name
    company_linkedin_url = request.company_linkedin_url

    if not company_name:
        company_row = await pool.fetchrow("""
            SELECT name, linkedin_url FROM core.companies WHERE domain = $1
        """, domain)
        if company_row:
            company_name = company_row["name"]
            company_linkedin_url = company_linkedin_url or company_row["linkedin_url"]

    # Call Modal function
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                MODAL_LAST_FUNDING_DATE_DB_DIRECT_URL,
                json={
                    "domain": domain,
                    "company_name": company_name or domain,
                    "company_linkedin_url": company_linkedin_url,
                    "workflow_source": WORKFLOW_SOURCE_LAST_FUNDING_DATE
                }
            )

            if response.status_code != 200:
                return LastFundingDateDbDirectResponse(
                    success=False,
                    domain=domain,
                    error=f"Modal returned {response.status_code}: {response.text}"
                )

            result = response.json()
            return LastFundingDateDbDirectResponse(
                success=result.get("success", False),
                domain=domain,
                last_funding_date=result.get("last_funding_date"),
                funding_type=result.get("funding_type"),
                confidence=result.get("confidence"),
                error=result.get("error")
            )
    except Exception as e:
        return LastFundingDateDbDirectResponse(
            success=False,
            domain=domain,
            error=str(e)
        )


# =============================================================================
# Parallel AI Task Enrichment Endpoints (db-direct)
# =============================================================================

MODAL_PARALLEL_HQ_LOCATION_URL = f"{MODAL_BASE_URL}-infer-parallel-hq-location.modal.run"
MODAL_PARALLEL_INDUSTRY_URL = f"{MODAL_BASE_URL}-infer-parallel-industry.modal.run"
MODAL_PARALLEL_COMPETITORS_URL = f"{MODAL_BASE_URL}-infer-parallel-competitors.modal.run"


class ParallelHqLocationRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-task/hq-location/infer/db-direct"


class ParallelHqLocationResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    hq_country: Optional[str] = None
    error: Optional[str] = None


class ParallelIndustryRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-task/industry/infer/db-direct"


class ParallelIndustryResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    error: Optional[str] = None


class ParallelCompetitorsRequest(BaseModel):
    domain: str
    company_name: str
    company_linkedin_url: Optional[str] = None
    workflow_source: str = "parallel-task/competitors/infer/db-direct"


class ParallelCompetitorsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    competitors: Optional[list] = None
    error: Optional[str] = None


@router.post(
    "/companies/parallel-task/hq-location/infer/db-direct",
    response_model=ParallelHqLocationResponse,
    summary="Infer company HQ location using Parallel AI",
    description="Wrapper for Modal function: infer_parallel_hq_location"
)
async def parallel_hq_location(request: ParallelHqLocationRequest) -> ParallelHqLocationResponse:
    """
    Infer company HQ location using Parallel AI Task API.
    Writes directly to core.company_parallel_locations.
    """
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                MODAL_PARALLEL_HQ_LOCATION_URL,
                json=request.model_dump(exclude_none=True)
            )
            result = response.json()
            return ParallelHqLocationResponse(**result)
        except Exception as e:
            return ParallelHqLocationResponse(
                success=False,
                domain=request.domain,
                error=str(e)
            )


@router.post(
    "/companies/parallel-task/industry/infer/db-direct",
    response_model=ParallelIndustryResponse,
    summary="Infer company industry using Parallel AI",
    description="Wrapper for Modal function: infer_parallel_industry"
)
async def parallel_industry(request: ParallelIndustryRequest) -> ParallelIndustryResponse:
    """
    Infer company industry using Parallel AI Task API.
    Writes directly to core.company_parallel_industries.
    """
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                MODAL_PARALLEL_INDUSTRY_URL,
                json=request.model_dump(exclude_none=True)
            )
            result = response.json()
            return ParallelIndustryResponse(**result)
        except Exception as e:
            return ParallelIndustryResponse(
                success=False,
                domain=request.domain,
                error=str(e)
            )


@router.post(
    "/companies/parallel-task/competitors/infer/db-direct",
    response_model=ParallelCompetitorsResponse,
    summary="Infer company competitors using Parallel AI",
    description="Wrapper for Modal function: infer_parallel_competitors"
)
async def parallel_competitors(request: ParallelCompetitorsRequest) -> ParallelCompetitorsResponse:
    """
    Infer company competitors using Parallel AI Task API.
    Writes directly to core.company_parallel_competitors.
    """
    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            response = await client.post(
                MODAL_PARALLEL_COMPETITORS_URL,
                json=request.model_dump(exclude_none=True)
            )
            result = response.json()
            return ParallelCompetitorsResponse(**result)
        except Exception as e:
            return ParallelCompetitorsResponse(
                success=False,
                domain=request.domain,
                error=str(e)
            )


@router.post(
    "/companies/db/parallel-to-core/backfill",
    response_model=BackfillParallelToCoreResponse,
    summary="Backfill parallel extractions to core tables",
    description="Wrapper for Modal function: backfill_parallel_to_core"
)
async def backfill_parallel_to_core(request: BackfillParallelToCoreRequest) -> BackfillParallelToCoreResponse:
    """
    Backfill data from parallel extractions to core tables.

    - Backfills customer_domain from extracted.parallel_case_studies to core.company_customers
    - Backfills champions from extracted.parallel_case_study_champions to core.case_study_champions

    Modal function: backfill_parallel_to_core
    Modal URL: https://bencrane--hq-master-data-ingest-backfill-parallel-to-core.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-backfill-parallel-to-core.modal.run"

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return BackfillParallelToCoreResponse(**response.json())
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
    "/companies/db/case-study-champions/lookup",
    response_model=CaseStudyChampionsLookupResponse,
    summary="Lookup case study champions by vendor domain",
    description="Wrapper for Modal function: lookup_case_study_champions"
)
async def lookup_case_study_champions(request: CaseStudyChampionsLookupRequest) -> CaseStudyChampionsLookupResponse:
    """
    Lookup champions featured in case studies for a given vendor domain.

    Returns champion details including name, title, company, and LinkedIn URL.

    Modal function: lookup_case_study_champions
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-case-study-champions.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-case-study-champions.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return CaseStudyChampionsLookupResponse(**response.json())
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
    "/companies/db/case-study-champions-detailed/lookup",
    response_model=ChampionsDetailedLookupResponse,
    summary="Lookup case study champions with testimonials",
    description="Wrapper for Modal function: lookup_champions_detailed"
)
async def lookup_champions_detailed(request: ChampionsDetailedLookupRequest) -> ChampionsDetailedLookupResponse:
    """
    Lookup champions with testimonials for a given vendor domain.

    Returns champion details including testimonials from case studies.

    Modal function: lookup_champions_detailed
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-champions-detailed.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-champions-detailed.modal.run"

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ChampionsDetailedLookupResponse(**response.json())
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
