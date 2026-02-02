from pydantic import BaseModel, ConfigDict, Json
from typing import Optional, List, Any, Union, Dict
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


class LeadsQuickResponse(BaseModel):
    data: List[Lead]


class PastEmployerCountResponse(BaseModel):
    company_name: str
    domain: Optional[str] = None
    count: int


class PastEmployerBreakdownResponse(BaseModel):
    company_name: str
    domain: Optional[str] = None
    total: int
    by_job_function: Dict[str, int]


class PriorityCompanyCreate(BaseModel):
    company_name: str


class PriorityCompany(BaseModel):
    id: str
    company_name: str
    domain: Optional[str] = None
    total: int = 0
    engineering: int = 0
    sales: int = 0


class PriorityCompaniesResponse(BaseModel):
    data: List[PriorityCompany]


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


# Target Client Views
class TargetClientViewCreate(BaseModel):
    domain: str
    name: Optional[str] = None
    filters: dict
    endpoint: str = "/api/leads"


class TargetClientView(BaseModel):
    id: str
    domain: str
    name: Optional[str] = None
    slug: str
    filters: dict
    endpoint: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TargetClientViewResponse(BaseModel):
    data: TargetClientView
    url: str


# Auth Models
class Org(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    status: str = "active"
    services_enabled: Optional[Union[Dict, Json[Dict]]] = None
    max_email_accounts: int = 0
    max_linkedin_accounts: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class User(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    email_verified: bool = False
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


class UserWithOrg(BaseModel):
    user: User
    org: Optional[Org] = None
    role: Optional[str] = None


class SessionValidation(BaseModel):
    valid: bool
    user_id: Optional[str] = None
    expires_at: Optional[str] = None


class MagicLinkRequest(BaseModel):
    email: str


class MagicLinkResponse(BaseModel):
    success: bool
    message: str


class VerifyMagicLinkResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[User] = None
    message: Optional[str] = None


# Company Models
class Company(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: Optional[str] = None
    domain: Optional[str] = None
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    matched_industry: Optional[str] = None
    employee_range: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    lead_count: Optional[int] = None


class CompaniesResponse(BaseModel):
    data: List[Company]
    meta: PaginationMeta


# Person Models
class Person(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_slug: Optional[str] = None
    full_name: Optional[str] = None
    core_company_id: Optional[str] = None
    linkedin_url_type: Optional[str] = None
    linkedin_user_profile_urn: Optional[str] = None
    person_city: Optional[str] = None
    person_state: Optional[str] = None
    person_country: Optional[str] = None
    matched_cleaned_job_title: Optional[str] = None
    matched_job_function: Optional[str] = None
    matched_seniority: Optional[str] = None
    job_start_date: Optional[date] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PeopleResponse(BaseModel):
    data: List[Person]
    meta: PaginationMeta
