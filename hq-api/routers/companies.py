from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from db import core, extracted
from models import Company, CompaniesResponse, PaginationMeta

router = APIRouter(prefix="/api/companies", tags=["companies"])

COMPANY_COLUMNS = ",".join([
    "id", "domain", "name", "linkedin_url",
    "company_city", "company_state", "company_country",
    "matched_industry", "employee_range"
])


def apply_company_filters(query, params: dict):
    """Apply company filters to a query."""
    if params.get("industry"):
        industries = params["industry"].split(",")
        query = query.in_("matched_industry", industries)
    if params.get("employee_range"):
        ranges = params["employee_range"].split(",")
        query = query.in_("employee_range", ranges)
    if params.get("city"):
        query = query.ilike("company_city", f"%{params['city']}%")
    if params.get("state"):
        query = query.ilike("company_state", f"%{params['state']}%")
    if params.get("country"):
        query = query.ilike("company_country", f"%{params['country']}%")
    if params.get("domain"):
        query = query.eq("domain", params["domain"])
    if params.get("name"):
        query = query.ilike("name", f"%{params['name']}%")
    return query


@router.get("", response_model=CompaniesResponse)
async def get_companies(
    industry: Optional[str] = Query(None, description="Filter by industry (comma-separated)"),
    employee_range: Optional[str] = Query(None, description="Filter by employee range (comma-separated)"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    country: Optional[str] = Query(None, description="Filter by country"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    name: Optional[str] = Query(None, description="Filter by company name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get companies with optional filters."""
    params = {
        "industry": industry,
        "employee_range": employee_range,
        "city": city,
        "state": state,
        "country": country,
        "domain": domain,
        "name": name,
    }

    # Get count
    count_query = core().from_("companies_full").select("id", count="exact", head=True)
    count_query = apply_company_filters(count_query, params)
    count_result = count_query.execute()
    total = count_result.count or 0

    # Get data
    data_query = core().from_("companies_full").select(COMPANY_COLUMNS)
    data_query = apply_company_filters(data_query, params)
    data_query = data_query.range(offset, offset + limit - 1)
    data_result = data_query.execute()

    return CompaniesResponse(
        data=[Company(**row) for row in data_result.data],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


@router.get("/search", response_model=CompaniesResponse)
async def search_companies(
    q: str = Query(..., min_length=2, description="Search query (name or domain)"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search companies by name or domain for autocomplete."""
    # Search by name OR domain matching the query
    data_query = (
        core()
        .from_("companies_full")
        .select(COMPANY_COLUMNS)
        .or_(f"name.ilike.%{q}%,domain.ilike.%{q}%")
        .limit(limit)
    )
    data_result = data_query.execute()

    return CompaniesResponse(
        data=[Company(**row) for row in data_result.data],
        meta=PaginationMeta(total=len(data_result.data), limit=limit, offset=0)
    )


@router.get("/lookup")
async def lookup_company_domain(
    name: str = Query(..., min_length=2, description="Company name to lookup"),
):
    """
    Lookup company domain by name.
    Returns the best matching domain for a given company name.
    """
    # Search for exact match first (case-insensitive)
    exact_result = (
        core()
        .from_("companies_full")
        .select("domain, name")
        .ilike("name", name)
        .limit(1)
        .execute()
    )

    if exact_result.data:
        return {
            "found": True,
            "domain": exact_result.data[0]["domain"],
            "name": exact_result.data[0]["name"],
            "match_type": "exact"
        }

    # Fall back to partial match
    partial_result = (
        core()
        .from_("companies_full")
        .select("domain, name")
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )

    if partial_result.data:
        return {
            "found": True,
            "domain": partial_result.data[0]["domain"],
            "name": partial_result.data[0]["name"],
            "match_type": "partial"
        }

    return {
        "found": False,
        "domain": None,
        "name": None,
        "match_type": None
    }


@router.get("/{domain}/customer-insights")
async def get_company_customer_insights(domain: str):
    """
    Get insights about a company's customers:
    - Industries of customer companies
    - Job titles of people featured in case studies/testimonials
    """
    # 1. Get customer domains
    customers_result = (
        core()
        .from_("company_customers")
        .select("customer_domain")
        .eq("origin_company_domain", domain)
        .execute()
    )

    customer_domains = list(set(
        row["customer_domain"] for row in customers_result.data
        if row.get("customer_domain")
    ))

    # 2. Get industries from companies_full for these customers
    industries = []
    if customer_domains:
        industries_result = (
            core()
            .from_("companies_full")
            .select("matched_industry")
            .in_("domain", customer_domains)
            .execute()
        )
        # Get unique non-null industries
        industries = list(set(
            row["matched_industry"] for row in industries_result.data
            if row.get("matched_industry")
        ))
        industries.sort()

    # 3. Get case study champions' job titles
    # Query case_study_details to find case studies for this origin company,
    # then get champions from those case studies
    case_studies_result = (
        extracted()
        .from_("case_study_details")
        .select("id")
        .eq("origin_company_domain", domain)
        .execute()
    )

    job_titles = []
    champions = []
    if case_studies_result.data:
        case_study_ids = [row["id"] for row in case_studies_result.data]

        champions_result = (
            extracted()
            .from_("case_study_champions")
            .select("full_name, job_title, company_name")
            .in_("case_study_id", case_study_ids)
            .execute()
        )

        # Extract unique job titles
        job_titles = list(set(
            row["job_title"] for row in champions_result.data
            if row.get("job_title")
        ))
        job_titles.sort()

        # Also return the full champion list for reference
        champions = champions_result.data

    return {
        "origin_domain": domain,
        "customer_count": len(customer_domains),
        "customer_industries": industries,
        "case_study_job_titles": job_titles,
        "case_study_champions": champions
    }


@router.get("/{domain}/customers")
async def get_company_customers(
    domain: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get customer companies for a given company domain.
    Returns enriched customer data including name, domain, industry, employee range, and country.
    """
    # Get customer domains from company_customers table
    customers_result = (
        core()
        .from_("company_customers")
        .select("customer_domain")
        .eq("origin_company_domain", domain)
        .execute()
    )

    if not customers_result.data:
        return {
            "data": [],
            "meta": {"total": 0, "limit": limit, "offset": offset, "origin_domain": domain}
        }

    # Extract unique customer domains
    customer_domains = list(set(
        row["customer_domain"] for row in customers_result.data
        if row.get("customer_domain")
    ))

    if not customer_domains:
        return {
            "data": [],
            "meta": {"total": 0, "limit": limit, "offset": offset, "origin_domain": domain}
        }

    total = len(customer_domains)

    # Apply pagination to domains list
    paginated_domains = customer_domains[offset:offset + limit]

    # Get enriched company data for these domains
    enriched_result = (
        core()
        .from_("companies_full")
        .select("name, domain, matched_industry, employee_range, company_country")
        .in_("domain", paginated_domains)
        .execute()
    )

    return {
        "data": enriched_result.data,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "origin_domain": domain
        }
    }


@router.get("/{domain}", response_model=Company)
async def get_company_by_domain(domain: str):
    """Get a single company by domain with full details."""
    # Get company from companies_full
    company_result = (
        core()
        .from_("companies_full")
        .select(COMPANY_COLUMNS)
        .eq("domain", domain)
        .execute()
    )

    if not company_result.data:
        raise HTTPException(status_code=404, detail="Company not found")

    company_data = company_result.data[0]

    # Get description
    desc_result = (
        core()
        .from_("company_descriptions")
        .select("description, tagline")
        .eq("domain", domain)
        .execute()
    )

    if desc_result.data:
        company_data["description"] = desc_result.data[0].get("description")
        company_data["tagline"] = desc_result.data[0].get("tagline")

    # Get lead count at this company
    lead_count_result = (
        core()
        .from_("leads")
        .select("person_id", count="exact", head=True)
        .eq("company_domain", domain)
        .execute()
    )
    company_data["lead_count"] = lead_count_result.count or 0

    return Company(**company_data)
