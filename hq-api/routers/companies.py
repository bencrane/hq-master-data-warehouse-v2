import os
import httpx
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from db import core, extracted, get_pool
from models import Company, CompaniesResponse, PaginationMeta

MODAL_SIMILAR_COMPANIES_URL = os.getenv(
    "MODAL_SIMILAR_COMPANIES_URL",
    "https://bencrane--hq-master-data-ingest-find-similar-companies-single.modal.run"
)

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


@router.get("/{domain}/has-customers")
async def check_has_customers(domain: str):
    """
    Simple check: does this company have customer data?
    Returns: { "has_customers": true/false, "count": N }
    """
    result = (
        core()
        .from_("company_customers")
        .select("customer_domain", count="exact", head=True)
        .eq("origin_company_domain", domain)
        .execute()
    )
    count = result.count or 0
    return {
        "domain": domain,
        "has_customers": count > 0,
        "count": count
    }


@router.post("/check-has-customers")
async def check_has_customers_post(payload: dict):
    """
    Simple check via POST: does this company have customer data?
    Payload: { "domain": "example.com" }
    Returns: { "has_customers": true/false, "count": N }
    """
    domain = payload.get("domain", "").lower().strip().rstrip("/")
    if not domain:
        return {"error": "domain is required", "has_customers": False, "count": 0}

    result = (
        core()
        .from_("company_customers")
        .select("customer_domain", count="exact", head=True)
        .eq("origin_company_domain", domain)
        .execute()
    )
    count = result.count or 0
    return {
        "domain": domain,
        "has_customers": count > 0,
        "count": count
    }


@router.get("/{domain}/has-case-studies")
async def check_has_case_studies(domain: str):
    """
    Check if case study details have been extracted for this company.
    Returns: { "has_case_studies": true/false, "count": N, "last_extracted_at": timestamp }
    """
    from db import get_pool
    pool = get_pool()

    domain = domain.lower().strip().rstrip("/")

    row = await pool.fetchrow("""
        SELECT
            COUNT(*) as count,
            MAX(created_at) as last_extracted_at
        FROM extracted.case_study_details
        WHERE origin_company_domain = $1
    """, domain)

    count = row["count"] if row else 0
    last_extracted_at = row["last_extracted_at"] if row else None

    return {
        "domain": domain,
        "has_case_studies": count > 0,
        "count": count,
        "last_extracted_at": str(last_extracted_at) if last_extracted_at else None
    }


@router.post("/check-has-case-studies")
async def check_has_case_studies_post(payload: dict):
    """
    Simple check via POST: does this company have case study details extracted?
    Payload: { "domain": "example.com" }
    Returns: { "has_case_studies": true/false, "count": N, "last_extracted_at": timestamp }
    """
    from db import get_pool
    pool = get_pool()

    domain = payload.get("domain", "").lower().strip().rstrip("/")
    if not domain:
        return {"error": "domain is required", "has_case_studies": False, "count": 0}

    row = await pool.fetchrow("""
        SELECT
            COUNT(*) as count,
            MAX(created_at) as last_extracted_at
        FROM extracted.case_study_details
        WHERE origin_company_domain = $1
    """, domain)

    count = row["count"] if row else 0
    last_extracted_at = row["last_extracted_at"] if row else None

    return {
        "domain": domain,
        "has_case_studies": count > 0,
        "count": count,
        "last_extracted_at": str(last_extracted_at) if last_extracted_at else None
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


@router.get("/{domain}/icp")
async def get_company_icp(domain: str):
    """
    Get ICP criteria and data for a company.
    Returns industries, job titles, countries, employee ranges, value proposition, and customer domains.
    """
    # Try core.icp_criteria first (unified table)
    criteria_result = (
        core()
        .from_("icp_criteria")
        .select("*")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )

    # Get customer domains
    customers_result = (
        core()
        .from_("company_customers")
        .select("customer_domain")
        .eq("origin_company_domain", domain)
        .execute()
    )
    customer_domains = [
        c["customer_domain"] for c in (customers_result.data or [])
        if c.get("customer_domain")
    ]

    if criteria_result.data and len(criteria_result.data) > 0:
        data = criteria_result.data[0]
        return {
            "success": True,
            "domain": domain,
            "company_name": data.get("company_name"),
            "customer_domains": customer_domains,
            "industries": data.get("industries"),
            "countries": data.get("countries"),
            "employee_ranges": data.get("employee_ranges"),
            "funding_stages": data.get("funding_stages"),
            "job_titles": data.get("job_titles"),
            "seniorities": data.get("seniorities"),
            "job_functions": data.get("job_functions"),
            "value_proposition": data.get("value_proposition"),
            "core_benefit": data.get("core_benefit"),
            "target_customer": data.get("target_customer"),
            "key_differentiator": data.get("key_differentiator"),
        }

    # Fallback to extracted tables
    # Get company name
    company_result = (
        core()
        .from_("companies")
        .select("name, cleaned_name")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    company_name = None
    if company_result.data and len(company_result.data) > 0:
        company_name = company_result.data[0].get("cleaned_name") or company_result.data[0].get("name")

    # Get ICP industries
    industries_result = (
        extracted()
        .from_("icp_industries")
        .select("matched_industries")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    industries = industries_result.data[0].get("matched_industries") if industries_result.data and len(industries_result.data) > 0 else None

    # Get ICP job titles - flatten
    job_titles_result = (
        extracted()
        .from_("icp_job_titles")
        .select("primary_titles, influencer_titles, extended_titles")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    job_titles = None
    if job_titles_result.data and len(job_titles_result.data) > 0:
        primary = job_titles_result.data[0].get("primary_titles") or []
        influencer = job_titles_result.data[0].get("influencer_titles") or []
        extended = job_titles_result.data[0].get("extended_titles") or []
        job_titles = primary + influencer + extended

    # Get value proposition
    value_prop_result = (
        extracted()
        .from_("icp_value_proposition")
        .select("value_proposition, core_benefit, target_customer, key_differentiator")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    value_proposition = None
    core_benefit = None
    target_customer = None
    key_differentiator = None
    if value_prop_result.data and len(value_prop_result.data) > 0:
        value_proposition = value_prop_result.data[0].get("value_proposition")
        core_benefit = value_prop_result.data[0].get("core_benefit")
        target_customer = value_prop_result.data[0].get("target_customer")
        key_differentiator = value_prop_result.data[0].get("key_differentiator")

    return {
        "success": True,
        "domain": domain,
        "company_name": company_name,
        "customer_domains": customer_domains,
        "industries": industries,
        "countries": None,
        "employee_ranges": None,
        "funding_stages": None,
        "job_titles": job_titles,
        "seniorities": None,
        "job_functions": None,
        "value_proposition": value_proposition,
        "core_benefit": core_benefit,
        "target_customer": target_customer,
        "key_differentiator": key_differentiator,
    }


@router.get("/{domain}/similar")
async def get_similar_companies(
    domain: str,
    refresh: bool = Query(False, description="Force refresh from API even if cached"),
    limit: int = Query(25, ge=1, le=100),
):
    """
    Get similar companies for a domain.

    First checks the database cache. If no data exists (or refresh=True),
    calls the Modal function to fetch from companyenrich.com API.
    """
    domain = domain.lower().strip()

    # Check cache first (unless refresh requested)
    if not refresh:
        cached_result = (
            extracted()
            .from_("company_enrich_similar")
            .select("company_name, company_domain, company_industry, company_description, similarity_score")
            .eq("input_domain", domain)
            .order("similarity_score", desc=True)
            .limit(limit)
            .execute()
        )

        if cached_result.data and len(cached_result.data) > 0:
            return {
                "success": True,
                "domain": domain,
                "source": "cache",
                "similar_companies": cached_result.data,
                "count": len(cached_result.data),
            }

    # No cache or refresh requested - call Modal function
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                MODAL_SIMILAR_COMPANIES_URL,
                json={
                    "domain": domain,
                    "similarity_weight": 0.0,
                    "country_code": None,
                },
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "domain": domain,
                    "error": f"Modal function returned {response.status_code}",
                    "detail": response.text[:500],
                }

            modal_result = response.json()

            if not modal_result.get("success"):
                return {
                    "success": False,
                    "domain": domain,
                    "error": modal_result.get("error", "Unknown error from Modal"),
                }

            # Fetch the newly stored results from DB
            fresh_result = (
                extracted()
                .from_("company_enrich_similar")
                .select("company_name, company_domain, company_industry, company_description, similarity_score")
                .eq("input_domain", domain)
                .order("similarity_score", desc=True)
                .limit(limit)
                .execute()
            )

            return {
                "success": True,
                "domain": domain,
                "source": "api",
                "similar_companies": fresh_result.data,
                "count": len(fresh_result.data) if fresh_result.data else 0,
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "domain": domain,
            "error": "Request to companyenrich API timed out (60s limit)",
            "suggestion": "Try again later or check if domain is valid",
        }
    except Exception as e:
        return {
            "success": False,
            "domain": domain,
            "error": str(e),
        }


@router.get("/by-technology")
async def get_companies_by_technology(
    name: str = Query(..., description="Technology name (e.g., Salesforce, Snowflake)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get companies using a specific technology.
    Searches the PredictLeads tech stack data.
    """
    pool = get_pool()

    # Get domains using this technology
    query = """
        SELECT DISTINCT c.domain
        FROM core.company_predictleads_technologies c
        JOIN reference.predictleads_technologies r ON r.id = c.technology_id
        WHERE r.title ILIKE $1
        ORDER BY c.domain
        LIMIT $2 OFFSET $3
    """
    count_query = """
        SELECT COUNT(DISTINCT c.domain)
        FROM core.company_predictleads_technologies c
        JOIN reference.predictleads_technologies r ON r.id = c.technology_id
        WHERE r.title ILIKE $1
    """

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, f"%{name}%")
        rows = await conn.fetch(query, f"%{name}%", limit, offset)

    domains = [row["domain"] for row in rows]

    # Get company details for these domains
    if domains:
        companies_result = (
            core()
            .from_("companies_full")
            .select(COMPANY_COLUMNS)
            .in_("domain", domains)
            .execute()
        )
        companies = companies_result.data
    else:
        companies = []

    return {
        "data": companies,
        "meta": {
            "total": total or 0,
            "limit": limit,
            "offset": offset,
            "technology": name,
        }
    }


@router.get("/by-job-title")
async def get_companies_by_job_title(
    title: str = Query(..., description="Job title (e.g., Software Engineer, Sales)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get companies hiring for a specific job title.
    Searches the job postings data by normalized_title.
    """
    pool = get_pool()

    # Get domains with this job title
    query = """
        SELECT DISTINCT c.domain
        FROM core.company_job_postings c
        JOIN reference.job_titles r ON r.id = c.job_title_id
        WHERE r.normalized_title ILIKE $1
        ORDER BY c.domain
        LIMIT $2 OFFSET $3
    """
    count_query = """
        SELECT COUNT(DISTINCT c.domain)
        FROM core.company_job_postings c
        JOIN reference.job_titles r ON r.id = c.job_title_id
        WHERE r.normalized_title ILIKE $1
    """

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_query, f"%{title}%")
        rows = await conn.fetch(query, f"%{title}%", limit, offset)

    domains = [row["domain"] for row in rows]

    # Get company details for these domains
    if domains:
        companies_result = (
            core()
            .from_("companies_full")
            .select(COMPANY_COLUMNS)
            .in_("domain", domains)
            .execute()
        )
        companies = companies_result.data
    else:
        companies = []

    return {
        "data": companies,
        "meta": {
            "total": total or 0,
            "limit": limit,
            "offset": offset,
            "job_title": title,
        }
    }


@router.get("/by-google-ads")
async def get_companies_running_google_ads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get companies running Google ads.
    """
    # Get count
    count_result = (
        core()
        .from_("company_google_ads")
        .select("id", count="exact", head=True)
        .eq("is_running_ads", True)
        .execute()
    )
    total = count_result.count or 0

    # Get domains running ads
    ads_result = (
        core()
        .from_("company_google_ads")
        .select("domain, ad_count, advertiser_id, last_checked_at")
        .eq("is_running_ads", True)
        .order("ad_count", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    domains = [row["domain"] for row in ads_result.data]

    # Get company details
    companies = []
    if domains:
        companies_result = (
            core()
            .from_("companies_full")
            .select(COMPANY_COLUMNS)
            .in_("domain", domains)
            .execute()
        )
        # Merge with ad data
        company_map = {c["domain"]: c for c in companies_result.data}
        for ad_row in ads_result.data:
            if ad_row["domain"] in company_map:
                merged = {**company_map[ad_row["domain"]], "ad_count": ad_row["ad_count"]}
                companies.append(merged)

    return {
        "data": companies,
        "meta": {"total": total, "limit": limit, "offset": offset}
    }


@router.get("/by-linkedin-ads")
async def get_companies_running_linkedin_ads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get companies running LinkedIn ads.
    """
    # Get count
    count_result = (
        core()
        .from_("company_linkedin_ads")
        .select("id", count="exact", head=True)
        .eq("is_running_ads", True)
        .execute()
    )
    total = count_result.count or 0

    # Get domains running ads
    ads_result = (
        core()
        .from_("company_linkedin_ads")
        .select("domain, ad_count, page_id, last_checked_at")
        .eq("is_running_ads", True)
        .order("ad_count", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    domains = [row["domain"] for row in ads_result.data]

    # Get company details
    companies = []
    if domains:
        companies_result = (
            core()
            .from_("companies_full")
            .select(COMPANY_COLUMNS)
            .in_("domain", domains)
            .execute()
        )
        company_map = {c["domain"]: c for c in companies_result.data}
        for ad_row in ads_result.data:
            if ad_row["domain"] in company_map:
                merged = {**company_map[ad_row["domain"]], "ad_count": ad_row["ad_count"]}
                companies.append(merged)

    return {
        "data": companies,
        "meta": {"total": total, "limit": limit, "offset": offset}
    }


@router.get("/by-meta-ads")
async def get_companies_running_meta_ads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get companies running Meta (Facebook/Instagram) ads.
    """
    # Get count
    count_result = (
        core()
        .from_("company_meta_ads")
        .select("id", count="exact", head=True)
        .eq("is_running_ads", True)
        .execute()
    )
    total = count_result.count or 0

    # Get domains running ads
    ads_result = (
        core()
        .from_("company_meta_ads")
        .select("domain, ad_count, page_id, platforms, last_checked_at")
        .eq("is_running_ads", True)
        .order("ad_count", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )

    domains = [row["domain"] for row in ads_result.data]

    # Get company details
    companies = []
    if domains:
        companies_result = (
            core()
            .from_("companies_full")
            .select(COMPANY_COLUMNS)
            .in_("domain", domains)
            .execute()
        )
        company_map = {c["domain"]: c for c in companies_result.data}
        for ad_row in ads_result.data:
            if ad_row["domain"] in company_map:
                merged = {
                    **company_map[ad_row["domain"]],
                    "ad_count": ad_row["ad_count"],
                    "platforms": ad_row["platforms"],
                }
                companies.append(merged)

    return {
        "data": companies,
        "meta": {"total": total, "limit": limit, "offset": offset}
    }


@router.get("/{domain}/ads")
async def get_company_ads(domain: str):
    """
    Get all ad platform data for a specific company.
    Returns Google, LinkedIn, and Meta ad status and counts.
    """
    domain = domain.lower().strip()

    # Google Ads
    google_result = (
        core()
        .from_("company_google_ads")
        .select("is_running_ads, ad_count, advertiser_id, last_checked_at")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    google_ads = google_result.data[0] if google_result.data else None

    # LinkedIn Ads
    linkedin_result = (
        core()
        .from_("company_linkedin_ads")
        .select("is_running_ads, ad_count, page_id, last_checked_at")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    linkedin_ads = linkedin_result.data[0] if linkedin_result.data else None

    # Meta Ads
    meta_result = (
        core()
        .from_("company_meta_ads")
        .select("is_running_ads, ad_count, page_id, platforms, last_checked_at")
        .eq("domain", domain)
        .limit(1)
        .execute()
    )
    meta_ads = meta_result.data[0] if meta_result.data else None

    return {
        "domain": domain,
        "google_ads": google_ads,
        "linkedin_ads": linkedin_ads,
        "meta_ads": meta_ads,
        "is_running_any_ads": any([
            google_ads and google_ads.get("is_running_ads"),
            linkedin_ads and linkedin_ads.get("is_running_ads"),
            meta_ads and meta_ads.get("is_running_ads"),
        ])
    }


@router.post("/enrichment-status")
async def check_company_enrichment_status(payload: dict):
    """
    Check if a company has been enriched by a specific workflow.

    Payload: {
        "company_name": "Acme Inc",        # optional (for clarity)
        "domain": "acme.com",              # required
        "company_linkedin_url": "...",     # optional
        "workflow_slug": "clay-company-firmographics"  # required
    }

    Returns: { "enriched": true/false, "last_enriched_at": timestamp }
    """
    from db import get_pool, reference

    domain = payload.get("domain", "").lower().strip().rstrip("/")
    workflow_slug = payload.get("workflow_slug", "").strip()

    if not domain:
        return {"error": "domain is required", "enriched": False}
    if not workflow_slug:
        return {"error": "workflow_slug is required", "enriched": False}

    # Look up core_table from registry
    registry_result = (
        reference()
        .from_("enrichment_workflow_registry")
        .select("core_table")
        .eq("workflow_slug", workflow_slug)
        .limit(1)
        .execute()
    )

    if not registry_result.data:
        return {
            "error": f"workflow_slug '{workflow_slug}' not found in registry",
            "enriched": False
        }

    core_table = registry_result.data[0].get("core_table")

    if not core_table:
        return {
            "error": f"workflow '{workflow_slug}' has no core_table mapped",
            "enriched": False,
            "note": "This workflow may not write to core schema"
        }

    # Query the core table for this domain
    pool = get_pool()

    # Parse schema and table name
    if "." in core_table:
        schema, table = core_table.split(".", 1)
    else:
        schema, table = "core", core_table

    row = await pool.fetchrow(f"""
        SELECT COUNT(*) as count, MAX(created_at) as last_enriched_at
        FROM {schema}.{table}
        WHERE domain = $1
    """, domain)

    count = row["count"] if row else 0
    last_enriched_at = row["last_enriched_at"] if row else None

    return {
        "domain": domain,
        "workflow_slug": workflow_slug,
        "core_table": core_table,
        "enriched": count > 0,
        "count": count,
        "last_enriched_at": str(last_enriched_at) if last_enriched_at else None
    }


@router.post("/companyenrich-status")
async def check_companyenrich_status(payload: dict):
    """
    Check if a company has been enriched via companyenrich.com.

    Payload: { "domain": "example.com" }

    Returns whether the domain exists in extracted.companyenrich_company
    and when it was enriched.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "enriched": False}

    row = await pool.fetchrow("""
        SELECT id, created_at
        FROM extracted.companyenrich_company
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "enriched": True,
            "extracted_id": str(row["id"]),
            "enriched_at": str(row["created_at"])
        }
    else:
        return {
            "domain": domain,
            "enriched": False,
            "extracted_id": None,
            "enriched_at": None
        }


@router.post("/firmographics-status")
async def check_firmographics_status(payload: dict):
    """
    Check if a company has firmographics data (from Clay/LinkedIn).

    Payload: { "domain": "example.com" }

    Returns whether the domain exists in extracted.company_firmographics
    and when it was enriched.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "enriched": False}

    row = await pool.fetchrow("""
        SELECT id, created_at
        FROM extracted.company_firmographics
        WHERE company_domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "enriched": True,
            "extracted_id": str(row["id"]),
            "enriched_at": str(row["created_at"])
        }
    else:
        return {
            "domain": domain,
            "enriched": False,
            "extracted_id": None,
            "enriched_at": None
        }


@router.post("/pricing-page-url")
async def get_pricing_page_url(payload: dict):
    """
    Get pricing page URL for a domain.

    Payload: { "domain": "example.com" }

    Returns whether we have a pricing_page_url and its value.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT pricing_page_url
        FROM core.ancillary_urls
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row and row["pricing_page_url"]:
        return {
            "domain": domain,
            "found": True,
            "pricing_page_url": row["pricing_page_url"]
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "pricing_page_url": None
        }


@router.post("/g2-page-url")
async def get_g2_page_url(payload: dict):
    """
    Get G2 page URL for a domain.

    Payload: { "domain": "example.com" }

    Returns whether we have a g2_url and its value.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT g2_url
        FROM core.company_social_urls
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row and row["g2_url"]:
        return {
            "domain": domain,
            "found": True,
            "g2_url": row["g2_url"]
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "g2_url": None
        }


@router.post("/social-urls")
async def get_social_urls(payload: dict):
    """
    Get all social URLs for a domain.

    Payload: { "domain": "example.com" }
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT linkedin_url, twitter_url, facebook_url, github_url,
               youtube_url, instagram_url, crunchbase_url, g2_url, angellist_url
        FROM core.company_social_urls
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "found": True,
            "linkedin_url": row["linkedin_url"],
            "twitter_url": row["twitter_url"],
            "facebook_url": row["facebook_url"],
            "github_url": row["github_url"],
            "youtube_url": row["youtube_url"],
            "instagram_url": row["instagram_url"],
            "crunchbase_url": row["crunchbase_url"],
            "g2_url": row["g2_url"],
            "angellist_url": row["angellist_url"]
        }
    else:
        return {
            "domain": domain,
            "found": False
        }


@router.post("/linkedin-ads-status")
async def get_linkedin_ads_status(payload: dict):
    """
    Check if we have LinkedIn ads data for a domain.

    Payload: { "domain": "example.com" }
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT is_running_ads, ad_count, created_at
        FROM core.company_linkedin_ads
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "found": True,
            "is_running_ads": row["is_running_ads"],
            "ad_count": row["ad_count"],
            "checked_at": str(row["created_at"])
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "is_running_ads": None,
            "ad_count": None,
            "checked_at": None
        }


@router.post("/google-ads-status")
async def get_google_ads_status(payload: dict):
    """
    Check if we have Google ads data for a domain.

    Payload: { "domain": "example.com" }
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT is_running_ads, ad_count, created_at
        FROM core.company_google_ads
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "found": True,
            "is_running_ads": row["is_running_ads"],
            "ad_count": row["ad_count"],
            "checked_at": str(row["created_at"])
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "is_running_ads": None,
            "ad_count": None,
            "checked_at": None
        }


@router.post("/meta-ads-status")
async def get_meta_ads_status(payload: dict):
    """
    Check if we have Meta ads data for a domain.

    Payload: { "domain": "example.com" }
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    row = await pool.fetchrow("""
        SELECT is_running_ads, ad_count, platforms, created_at
        FROM core.company_meta_ads
        WHERE domain = $1
        LIMIT 1
    """, domain)

    if row:
        return {
            "domain": domain,
            "found": True,
            "is_running_ads": row["is_running_ads"],
            "ad_count": row["ad_count"],
            "platforms": row["platforms"],
            "checked_at": str(row["created_at"])
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "is_running_ads": None,
            "ad_count": None,
            "platforms": None,
            "checked_at": None
        }


@router.post("/customers-status")
async def get_customers_status(payload: dict):
    """
    Check if we have customer data for a domain (as the origin company).

    Payload: { "domain": "example.com" }

    Returns count of customers and list of case study URLs.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    rows = await pool.fetch("""
        SELECT customer_name, customer_domain, case_study_url
        FROM core.company_customers
        WHERE origin_company_domain = $1
        ORDER BY customer_name
    """, domain)

    if rows:
        case_study_urls = [r["case_study_url"] for r in rows if r["case_study_url"]]
        return {
            "domain": domain,
            "found": True,
            "customer_count": len(rows),
            "case_study_url_count": len(case_study_urls),
            "case_study_urls": case_study_urls
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "customer_count": 0,
            "case_study_url_count": 0,
            "case_study_urls": []
        }


@router.post("/case-studies-status")
async def get_case_studies_status(payload: dict):
    """
    Check if we have extracted case study details for a domain (as the origin company).

    Payload: { "domain": "example.com" }

    Returns count and list of case study URLs.
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "found": False}

    rows = await pool.fetch("""
        SELECT case_study_url, company_customer_name, company_customer_domain
        FROM extracted.case_study_details
        WHERE origin_company_domain = $1
        ORDER BY created_at DESC
    """, domain)

    if rows:
        return {
            "domain": domain,
            "found": True,
            "case_study_count": len(rows),
            "case_study_urls": [r["case_study_url"] for r in rows]
        }
    else:
        return {
            "domain": domain,
            "found": False,
            "case_study_count": 0,
            "case_study_urls": []
        }


@router.post("/public-company-info")
async def get_public_company_info(payload: dict):
    """
    Get public company info (ticker and SEC CIK) for a domain.

    Payload: { "domain": "apple.com" }
    Returns ticker symbol and SEC CIK if the company is publicly traded.
    """
    domain = payload.get("domain", "").lower().strip()
    if not domain:
        return {"error": "domain is required", "found": False}

    pool = get_pool()

    # Get the most recent record with CIK data from raw.company_ticker_payloads
    row = await pool.fetchrow("""
        SELECT
            domain,
            payload->>'ticker' AS ticker,
            payload->>'sec_cik' AS cik,
            payload->>'sec_company_name' AS sec_company_name,
            created_at
        FROM raw.company_ticker_payloads
        WHERE domain = $1
          AND payload->>'sec_cik' IS NOT NULL
          AND payload->>'sec_cik' != 'null'
        ORDER BY created_at DESC
        LIMIT 1
    """, domain)

    if row:
        return {
            "found": True,
            "domain": row["domain"],
            "ticker": row["ticker"],
            "cik": row["cik"],
            "sec_company_name": row["sec_company_name"],
            "last_updated": str(row["created_at"]) if row["created_at"] else None
        }

    # Fallback: check if we have ticker without CIK
    fallback_row = await pool.fetchrow("""
        SELECT
            domain,
            payload->>'ticker' AS ticker,
            created_at
        FROM raw.company_ticker_payloads
        WHERE domain = $1
        ORDER BY created_at DESC
        LIMIT 1
    """, domain)

    if fallback_row:
        return {
            "found": True,
            "domain": fallback_row["domain"],
            "ticker": fallback_row["ticker"],
            "cik": None,
            "sec_company_name": None,
            "last_updated": str(fallback_row["created_at"]) if fallback_row["created_at"] else None,
            "note": "CIK not yet fetched from SEC"
        }

    return {
        "found": False,
        "domain": domain,
        "ticker": None,
        "cik": None,
        "sec_company_name": None
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


MODAL_DISCOVER_PRICING_PAGE_URL = os.getenv(
    "MODAL_DISCOVER_PRICING_PAGE_URL",
    "https://bencrane--hq-master-data-ingest-discover-pricing-page-url.modal.run"
)


@router.post("/discover-pricing-page")
async def discover_pricing_page(payload: dict):
    """
    Discover the pricing page URL for a company using Gemini.

    Takes a domain, fetches the homepage, and uses AI to find the pricing page URL.

    Payload: { "domain": "example.com", "company_name": "Example Inc" (optional) }

    Returns: { "success": true, "pricing_page_url": "...", "confidence": "high|medium|low" }
    """
    domain = payload.get("domain", "").lower().strip()
    if not domain:
        return {"error": "domain is required", "success": False}

    company_name = payload.get("company_name", "")

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            MODAL_DISCOVER_PRICING_PAGE_URL,
            json={"domain": domain, "company_name": company_name}
        )
        return response.json()


@router.post("/ingest-pricing-page-url")
async def ingest_pricing_page_url(payload: dict):
    """
    Ingest a pricing page URL from Clay.

    Payload: { "domain": "example.com", "pricing_page_url": "https://example.com/pricing" }
    """
    domain = payload.get("domain", "").lower().strip()
    pricing_page_url = payload.get("pricing_page_url", "").strip()

    if not domain:
        return {"error": "domain is required", "success": False}

    if not pricing_page_url:
        return {"error": "pricing_page_url is required", "success": False}

    pool = get_pool()
    await pool.execute("""
        INSERT INTO core.ancillary_urls (domain, pricing_page_url, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            pricing_page_url = EXCLUDED.pricing_page_url,
            updated_at = NOW()
    """, domain, pricing_page_url)

    return {
        "success": True,
        "domain": domain,
        "pricing_page_url": pricing_page_url
    }


OPENWEBNINJA_API_KEY = os.getenv(
    "OPENWEBNINJA_API_KEY",
    "ak_5h42dp58t37mjkhdf3920d38h0pybxj99pm1jf61mcie4x1"
)


@router.post("/discover-g2-page-openwebninja")
async def discover_g2_page_openwebninja(payload: dict):
    """
    Discover G2 page URL for a company using OpenWebNinja web search.

    Payload: { "domain": "example.com", "company_name": "Example Inc" }
    """
    import urllib.parse
    import re

    domain = payload.get("domain", "").lower().strip()
    company_name = payload.get("company_name", "").strip()

    if not domain:
        return {"error": "domain is required", "success": False}

    if not company_name:
        return {"error": "company_name is required", "success": False}

    # Build the search prompt
    prompt = f"Find the G2.com product page URL for {company_name} (website: {domain}). Return only the URL in format https://www.g2.com/products/..."

    # Call OpenWebNinja API
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://api.openwebninja.com/realtime-web-search/ai-mode?prompt={encoded_prompt}&gl=us&hl=en"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            headers={"x-api-key": OPENWEBNINJA_API_KEY}
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"OpenWebNinja API error: {response.status_code}",
                "domain": domain
            }

        result = response.json()

    # Extract G2 URL from response
    response_text = result.get("result", "") or result.get("answer", "") or str(result)

    # Find G2 URL pattern
    g2_match = re.search(r'https?://(?:www\.)?g2\.com/products/[^\s\'"<>]+', response_text)
    g2_url = g2_match.group(0) if g2_match else None

    # Clean up URL (remove trailing punctuation)
    if g2_url:
        g2_url = g2_url.rstrip('.,;:)')

    return {
        "success": True,
        "domain": domain,
        "company_name": company_name,
        "g2_url": g2_url
    }


MODAL_DISCOVER_G2_PAGE_GEMINI_URL = os.getenv(
    "MODAL_DISCOVER_G2_PAGE_GEMINI_URL",
    "https://bencrane--hq-master-data-ingest-discover-g2-page-gemini.modal.run"
)


@router.post("/discover-g2-page-gemini")
async def discover_g2_page_gemini(payload: dict):
    """
    Discover G2 page URL for a company using Gemini.

    Payload: { "domain": "example.com", "company_name": "Example Inc" }
    """
    domain = payload.get("domain", "").lower().strip()
    company_name = payload.get("company_name", "").strip()

    if not domain:
        return {"error": "domain is required", "success": False}

    if not company_name:
        return {"error": "company_name is required", "success": False}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            MODAL_DISCOVER_G2_PAGE_GEMINI_URL,
            json={"domain": domain, "company_name": company_name}
        )
        return response.json()


@router.post("/search-social-links-openwebninja")
async def search_social_links_openwebninja(payload: dict):
    """
    Search for social links using OpenWebNinja.

    Payload: {
        "query": "John Smith Acme Corp",
        "social_networks": "facebook,tiktok,instagram,snapchat,twitter,youtube,linkedin,github,pinterest"
    }

    social_networks is optional, defaults to all networks.
    """
    import urllib.parse

    query = payload.get("query", "").strip()
    social_networks = payload.get("social_networks", "facebook,tiktok,instagram,snapchat,twitter,youtube,linkedin,github,pinterest")

    if not query:
        return {"error": "query is required", "success": False}

    encoded_query = urllib.parse.quote(query)
    encoded_networks = urllib.parse.quote(social_networks)
    url = f"https://api.openwebninja.com/social-links-search/search-social-links?query={encoded_query}&social_networks={encoded_networks}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            headers={"x-api-key": OPENWEBNINJA_API_KEY}
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"OpenWebNinja API error: {response.status_code}"
            }

        return response.json()


MODAL_DISCOVER_COMPETITORS_URL = os.getenv(
    "MODAL_DISCOVER_COMPETITORS_URL",
    "https://bencrane--hq-master-data-ingest-discover-competitors-openai.modal.run"
)


@router.post("/discover-competitors-openai")
async def discover_competitors_openai(payload: dict):
    """
    Discover top 3-5 competitors using OpenAI.

    Payload: { "company_name": "Stripe", "domain": "stripe.com" }

    Returns: { "competitors": [{"name": "...", "domain": "...", "linkedin_url": "..."}] }
    """
    company_name = payload.get("company_name", "").strip()
    domain = payload.get("domain", "").lower().strip()

    if not company_name:
        return {"error": "company_name is required", "success": False}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            MODAL_DISCOVER_COMPETITORS_URL,
            json={"company_name": company_name, "domain": domain}
        )
        return response.json()


MODAL_INGEST_COMPETITORS_URL = os.getenv(
    "MODAL_INGEST_COMPETITORS_URL",
    "https://bencrane--hq-master-data-ingest-ingest-competitors.modal.run"
)


@router.post("/ingest-competitors")
async def ingest_competitors(payload: dict):
    """
    Ingest competitors data into raw/extracted/core tables.

    Payload: { "domain": "canva.com", "company_name": "Canva", "competitors": [...] }
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            MODAL_INGEST_COMPETITORS_URL,
            json=payload
        )
        return response.json()


@router.post("/competitors-status")
async def get_competitors_status(payload: dict):
    """
    Check if we have competitors for a domain.

    Payload: { "domain": "canva.com" }
    """
    pool = get_pool()
    domain = payload.get("domain", "").lower().strip()

    if not domain:
        return {"error": "domain is required", "has_competitors": False}

    row = await pool.fetchrow("""
        SELECT COUNT(*) as count
        FROM core.company_competitors
        WHERE domain = $1
    """, domain)

    count = row["count"] if row else 0

    return {
        "domain": domain,
        "has_competitors": count > 0,
        "competitor_count": count
    }


@router.post("/ingest-g2-page-url")
async def ingest_g2_page_url(payload: dict):
    """
    Ingest a G2 page URL from Clay.

    Payload: { "domain": "example.com", "g2_url": "https://www.g2.com/products/example" }
    """
    domain = payload.get("domain", "").lower().strip()
    g2_url = payload.get("g2_url", "").strip()

    if not domain:
        return {"error": "domain is required", "success": False}

    if not g2_url:
        return {"error": "g2_url is required", "success": False}

    pool = get_pool()
    await pool.execute("""
        INSERT INTO core.company_social_urls (domain, g2_url, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            g2_url = EXCLUDED.g2_url,
            updated_at = NOW()
    """, domain, g2_url)

    return {
        "success": True,
        "domain": domain,
        "g2_url": g2_url
    }
