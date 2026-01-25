from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import date


class Lead(BaseModel):
    model_config = ConfigDict(extra='ignore')

    person_id: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_slug: Optional[str] = None
    full_name: Optional[str] = None
    linkedin_url_type: Optional[str] = None
    linkedin_user_profile_urn: Optional[str] = None
    person_city: Optional[str] = None
    person_state: Optional[str] = None
    person_country: Optional[str] = None
    matched_cleaned_job_title: Optional[str] = None
    matched_job_function: Optional[str] = None
    matched_seniority: Optional[str] = None
    job_start_date: Optional[date] = None
    company_id: Optional[str] = None
    company_domain: Optional[str] = None
    company_name: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    matched_industry: Optional[str] = None
    employee_range: Optional[str] = None


class LeadRecentlyPromoted(Lead):
    previous_title: Optional[str] = None
    new_title: Optional[str] = None
    promotion_date: Optional[date] = None


class LeadAtVCPortfolio(Lead):
    vc_name: Optional[str] = None
    vc_company_description: Optional[str] = None


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class LeadsResponse(BaseModel):
    data: List[Lead]
    meta: PaginationMeta


class LeadsRecentlyPromotedResponse(BaseModel):
    data: List[LeadRecentlyPromoted]
    meta: PaginationMeta


class LeadsAtVCPortfolioResponse(BaseModel):
    data: List[LeadAtVCPortfolio]
    meta: PaginationMeta


class FilterOption(BaseModel):
    value: str
    count: int


class FiltersResponse(BaseModel):
    data: List[FilterOption]
