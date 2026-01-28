from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import date, datetime, timedelta
from db import core, get_pool
from models import (
    Lead, LeadsResponse, PaginationMeta,
    LeadRecentlyPromoted, LeadsRecentlyPromotedResponse,
    LeadAtVCPortfolio, LeadsAtVCPortfolioResponse
)

router = APIRouter(prefix="/api/leads", tags=["leads"])


def row_to_dict(row):
    """Convert asyncpg Record to dict, converting UUIDs to strings."""
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'hex'):  # UUID object
            d[k] = str(v)
    return d


# Column selections to avoid SELECT * issues with Supabase
LEAD_COLUMNS = ",".join([
    "person_id", "linkedin_url", "linkedin_slug", "full_name", "linkedin_url_type",
    "person_city", "person_state", "person_country",
    "matched_cleaned_job_title", "matched_job_function", "matched_seniority", "job_start_date",
    "company_id", "company_domain", "company_name", "company_linkedin_url",
    "company_city", "company_state", "company_country", "matched_industry", "employee_range"
])

LEAD_PROMOTED_COLUMNS = LEAD_COLUMNS + ",previous_title,new_title,promotion_date"
LEAD_VC_COLUMNS = LEAD_COLUMNS + ",vc_name,vc_company_description"


def apply_lead_filters(query, params: dict):
    """Apply common lead filters to a query."""
    # Required fields - exclude leads missing any of these
    query = query.not_.is_("company_name", "null")
    query = query.not_.is_("company_country", "null")
    query = query.not_.is_("person_country", "null")
    query = query.not_.is_("matched_job_function", "null")
    query = query.not_.is_("matched_seniority", "null")
    if params.get("job_function"):
        functions = params["job_function"].split(",")
        query = query.in_("matched_job_function", functions)
    if params.get("seniority"):
        seniorities = params["seniority"].split(",")
        query = query.in_("matched_seniority", seniorities)
    if params.get("industry"):
        industries = params["industry"].split(",")
        query = query.in_("matched_industry", industries)
    if params.get("employee_range"):
        ranges = params["employee_range"].split(",")
        query = query.in_("employee_range", ranges)
    if params.get("person_city"):
        query = query.ilike("person_city", f"%{params['person_city']}%")
    if params.get("person_state"):
        query = query.ilike("person_state", f"%{params['person_state']}%")
    if params.get("person_country"):
        query = query.ilike("person_country", f"%{params['person_country']}%")
    if params.get("company_city"):
        query = query.ilike("company_city", f"%{params['company_city']}%")
    if params.get("company_state"):
        query = query.ilike("company_state", f"%{params['company_state']}%")
    if params.get("company_country"):
        query = query.ilike("company_country", f"%{params['company_country']}%")
    if params.get("company_domain"):
        query = query.eq("company_domain", params["company_domain"])
    if params.get("company_name"):
        query = query.ilike("company_name", f"%{params['company_name']}%")
    if params.get("job_title"):
        query = query.ilike("matched_cleaned_job_title", f"%{params['job_title']}%")
    if params.get("full_name"):
        query = query.ilike("full_name", f"%{params['full_name']}%")
    if params.get("job_start_date_gte"):
        query = query.gte("job_start_date", params["job_start_date_gte"])
    if params.get("job_start_date_lte"):
        query = query.lte("job_start_date", params["job_start_date_lte"])
    return query


@router.get("", response_model=LeadsResponse)
async def get_leads(
    job_function: Optional[str] = Query(None, description="Filter by job function (comma-separated)"),
    seniority: Optional[str] = Query(None, description="Filter by seniority (comma-separated)"),
    industry: Optional[str] = Query(None, description="Filter by industry (comma-separated)"),
    employee_range: Optional[str] = Query(None, description="Filter by employee range (comma-separated)"),
    person_city: Optional[str] = Query(None),
    person_state: Optional[str] = Query(None),
    person_country: Optional[str] = Query(None),
    company_city: Optional[str] = Query(None),
    company_state: Optional[str] = Query(None),
    company_country: Optional[str] = Query(None),
    company_domain: Optional[str] = Query(None),
    company_name: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    full_name: Optional[str] = Query(None),
    job_start_date_gte: Optional[date] = Query(None),
    job_start_date_lte: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get leads with optional filters."""
    params = {
        "job_function": job_function, "seniority": seniority, "industry": industry,
        "employee_range": employee_range, "person_city": person_city, "person_state": person_state,
        "person_country": person_country, "company_city": company_city, "company_state": company_state,
        "company_country": company_country, "company_domain": company_domain, "company_name": company_name,
        "job_title": job_title, "full_name": full_name,
        "job_start_date_gte": str(job_start_date_gte) if job_start_date_gte else None,
        "job_start_date_lte": str(job_start_date_lte) if job_start_date_lte else None,
    }

    count_query = core().from_("leads").select("person_id", count="exact", head=True)
    count_query = apply_lead_filters(count_query, params)
    count_result = count_query.execute()
    total = count_result.count or 0

    data_query = core().from_("leads").select(LEAD_COLUMNS)
    data_query = apply_lead_filters(data_query, params)
    data_query = data_query.range(offset, offset + limit - 1)
    data_result = data_query.execute()

    return LeadsResponse(
        data=[Lead(**row) for row in data_result.data],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/recently-promoted", response_model=LeadsRecentlyPromotedResponse)
async def get_leads_recently_promoted(
    promoted_within_days: int = Query(180),
    job_function: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get leads who were recently promoted."""
    params = {"job_function": job_function, "seniority": seniority, "industry": industry}
    date_threshold = (datetime.now() - timedelta(days=promoted_within_days)).strftime("%Y-%m-%d")

    count_query = core().from_("leads_recently_promoted").select("person_id", count="exact", head=True)
    count_query = apply_lead_filters(count_query, params)
    count_query = count_query.gte("promotion_date", date_threshold)
    count_result = count_query.execute()
    total = count_result.count or 0

    data_query = core().from_("leads_recently_promoted").select(LEAD_PROMOTED_COLUMNS)
    data_query = apply_lead_filters(data_query, params)
    data_query = data_query.gte("promotion_date", date_threshold)
    data_query = data_query.order("promotion_date", desc=True)
    data_query = data_query.range(offset, offset + limit - 1)
    data_result = data_query.execute()

    return LeadsRecentlyPromotedResponse(
        data=[LeadRecentlyPromoted(**row) for row in data_result.data],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/new-in-role", response_model=LeadsResponse)
async def get_leads_new_in_role(
    started_within_days: int = Query(90),
    job_function: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get leads who recently started a new role."""
    params = {"job_function": job_function, "seniority": seniority, "industry": industry}
    date_threshold = (datetime.now() - timedelta(days=started_within_days)).strftime("%Y-%m-%d")

    count_query = core().from_("leads").select("person_id", count="exact", head=True)
    count_query = apply_lead_filters(count_query, params)
    count_query = count_query.gte("job_start_date", date_threshold)
    count_result = count_query.execute()
    total = count_result.count or 0

    data_query = core().from_("leads").select(LEAD_COLUMNS)
    data_query = apply_lead_filters(data_query, params)
    data_query = data_query.gte("job_start_date", date_threshold)
    data_query = data_query.order("job_start_date", desc=True)
    data_query = data_query.range(offset, offset + limit - 1)
    data_result = data_query.execute()

    return LeadsResponse(
        data=[Lead(**row) for row in data_result.data],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/at-vc-portfolio", response_model=LeadsAtVCPortfolioResponse)
async def get_leads_at_vc_portfolio(
    vc_name: Optional[str] = Query(None, description="Filter by VC firm name"),
    job_function: Optional[str] = Query(None),
    seniority: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get leads at VC portfolio companies."""
    params = {"job_function": job_function, "seniority": seniority}

    count_query = core().from_("leads_at_vc_portfolio").select("person_id", count="exact", head=True)
    count_query = apply_lead_filters(count_query, params)
    if vc_name:
        count_query = count_query.eq("vc_name", vc_name)
    count_result = count_query.execute()
    total = count_result.count or 0

    data_query = core().from_("leads_at_vc_portfolio").select(LEAD_VC_COLUMNS)
    data_query = apply_lead_filters(data_query, params)
    if vc_name:
        data_query = data_query.eq("vc_name", vc_name)
    data_query = data_query.range(offset, offset + limit - 1)
    data_result = data_query.execute()

    return LeadsAtVCPortfolioResponse(
        data=[LeadAtVCPortfolio(**row) for row in data_result.data],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/by-past-employer", response_model=LeadsResponse)
async def get_leads_by_past_employer(
    domains: str = Query(..., description="Comma-separated list of company domains"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Get leads who previously worked at specified companies.

    Uses PostgreSQL function core.get_leads_by_past_employer() for efficient querying.
    """
    domain_list = [d.strip().lower() for d in domains.split(",")]
    pool = get_pool()

    # Get data via direct PostgreSQL connection
    rows = await pool.fetch(
        "SELECT * FROM core.get_leads_by_past_employer($1, $2, $3)",
        domain_list, limit, offset
    )

    # Get total count
    count_row = await pool.fetchrow(
        "SELECT COUNT(*) FROM core.get_leads_by_past_employer($1, $2, $3)",
        domain_list, 100000, 0
    )
    total = count_row['count'] if count_row else 0

    return LeadsResponse(
        data=[Lead(**row_to_dict(row)) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/by-company-customers", response_model=LeadsResponse)
async def get_leads_by_company_customers(
    company_domain: str = Query(..., description="Domain of the origin company (e.g., 'forethought.ai')"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Get leads who previously worked at customers of the specified company.

    Looks up the company's customers from core.company_customers, then finds
    leads who have work history at those customer companies.
    """
    pool = get_pool()
    domain = company_domain.strip().lower()

    # Get data via direct PostgreSQL connection
    rows = await pool.fetch(
        "SELECT * FROM core.get_leads_by_company_customers($1, $2, $3)",
        domain, limit, offset
    )

    # Get total count
    count_row = await pool.fetchrow(
        "SELECT COUNT(*) FROM core.get_leads_by_company_customers($1, $2, $3)",
        domain, 100000, 0
    )
    total = count_row['count'] if count_row else 0

    return LeadsResponse(
        data=[Lead(**row_to_dict(row)) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )
