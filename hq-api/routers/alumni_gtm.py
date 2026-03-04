"""
AlumniGTM Leads Router

Returns qualified leads for AlumniGTM — people who previously worked at a client's
customers and now hold buying authority at new companies.
"""

from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from db import get_pool

router = APIRouter(prefix="/v1/alumni-gtm", tags=["alumni-gtm"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PersonData(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    picture_url: Optional[str] = None
    matched_seniority: Optional[str] = None
    matched_job_function: Optional[str] = None


class Firmographics(BaseModel):
    industry: Optional[str] = None
    employee_count: Optional[int] = None
    size_range: Optional[str] = None
    founded_year: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    description: Optional[str] = None


class StoreleadsData(BaseModel):
    platform: Optional[str] = None
    estimated_sales_yearly: Optional[float] = None
    product_count: Optional[int] = None
    rank: Optional[int] = None
    technologies: Optional[List[str]] = None


class AdsData(BaseModel):
    meta_ads_count: Optional[int] = 0
    google_ads_count: Optional[int] = 0


class CurrentCompany(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    role: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    firmographics: Optional[Firmographics] = None
    storeleads: Optional[StoreleadsData] = None
    ads: Optional[AdsData] = None


class PriorCompany(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gtm_fit: Optional[bool] = None
    gtm_fit_reason: Optional[str] = None


class Lead(BaseModel):
    person: PersonData
    current_company: CurrentCompany
    prior_company: PriorCompany


class PriorCompanySummary(BaseModel):
    name: Optional[str] = None
    domain: str
    lead_count: int


class AlumniGTMLeadsResponse(BaseModel):
    success: bool
    origin_company_domain: str
    total_leads: int
    total_prior_companies: int
    leads: List[Lead]
    prior_companies_summary: List[PriorCompanySummary]
    error: Optional[str] = None


class AlumniGTMLeadsRequest(BaseModel):
    origin_company_domain: str
    gtm_fit: Optional[bool] = None
    prior_company_domain: Optional[str] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0


# ---------------------------------------------------------------------------
# Main query — single JOIN that gets leads + enrichments in one pass.
# DISTINCT ON deduplicates when person_work_history has multiple rows.
# ---------------------------------------------------------------------------

LEADS_QUERY = """
SELECT DISTINCT ON (pt.person_linkedin_url, ct.target_company_domain)
    pt.full_name,
    pt.first_name,
    pt.last_name,
    pt.person_linkedin_url,
    pt.cleaned_job_title  AS current_role,
    pt.company_name       AS current_company_name,
    pt.domain             AS current_company_domain,
    pt.company_linkedin_url AS current_company_linkedin_url,

    ct.target_company_name   AS prior_company_name,
    ct.target_company_domain AS prior_company_domain,
    ct.target_company_linkedin_url AS prior_company_linkedin_url,
    ct.gtm_fit,
    ct.reason AS gtm_fit_reason,

    pwh.title      AS prior_role,
    pwh.start_date AS prior_start_date,
    pwh.end_date   AS prior_end_date,

    pp.headline,
    pp.location_name,
    pp.picture_url,
    pp.matched_seniority,
    pp.matched_job_function,

    cf.industry,
    cf.employee_count,
    cf.size_range,
    cf.founded_year,
    cf.country,
    cf.city,
    cf.state,
    cf.description AS company_description,

    sl.platform,
    sl.estimated_sales_yearly,
    sl.product_count,
    sl.rank AS storeleads_rank

FROM core.people_targets pt

JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1

LEFT JOIN core.person_work_history pwh
    ON pt.person_linkedin_url = pwh.linkedin_url
   AND pwh.company_domain = ct.target_company_domain

LEFT JOIN extracted.person_profile pp
    ON pt.person_linkedin_url = pp.linkedin_url

LEFT JOIN extracted.company_firmographics cf
    ON pt.domain = cf.company_domain

LEFT JOIN extracted.storeleads_company sl
    ON pt.domain = sl.domain

WHERE ($2::boolean IS NULL OR ct.gtm_fit = $2)
  AND ($3::text    IS NULL OR ct.target_company_domain = $3)

ORDER BY pt.person_linkedin_url, ct.target_company_domain, pwh.start_date DESC NULLS LAST
"""

COUNT_QUERY = """
SELECT count(DISTINCT (pt.person_linkedin_url, ct.target_company_domain)) AS total
FROM core.people_targets pt
JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1
WHERE ($2::boolean IS NULL OR ct.gtm_fit = $2)
  AND ($3::text    IS NULL OR ct.target_company_domain = $3)
"""

TECHNOLOGIES_QUERY = """
SELECT domain, name
FROM extracted.storeleads_technology
WHERE domain = ANY($1::text[])
"""

META_ADS_COUNT_QUERY = """
SELECT domain, count(*) AS cnt
FROM extracted.company_meta_ads
WHERE domain = ANY($1::text[])
GROUP BY domain
"""

GOOGLE_ADS_COUNT_QUERY = """
SELECT domain, count(*) AS cnt
FROM extracted.company_google_ads
WHERE domain = ANY($1::text[])
GROUP BY domain
"""

PRIOR_COMPANIES_SUMMARY_QUERY = """
SELECT
    ct.target_company_name AS name,
    ct.target_company_domain AS domain,
    count(DISTINCT pt.person_linkedin_url) AS lead_count
FROM core.people_targets pt
JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1
WHERE ($2::boolean IS NULL OR ct.gtm_fit = $2)
  AND ($3::text    IS NULL OR ct.target_company_domain = $3)
GROUP BY ct.target_company_domain, ct.target_company_name
ORDER BY lead_count DESC
"""


def _str_or_none(val) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


@router.post("/leads", response_model=AlumniGTMLeadsResponse)
async def get_alumni_gtm_leads(request: AlumniGTMLeadsRequest):
    """
    Get AlumniGTM leads for an origin company.
    Returns people who previously worked at the client's customers
    and now hold positions at new companies.
    """
    origin_domain = request.origin_company_domain.lower().strip()
    gtm_fit = request.gtm_fit
    prior_company_domain = request.prior_company_domain
    limit = min(request.limit or 100, 500)
    offset = request.offset or 0

    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            # Run count + paginated leads + summary concurrently-ish
            # (asyncpg doesn't support true parallel on one conn, but we
            #  keep it in one connection to avoid pool pressure)
            total_row = await conn.fetchrow(
                COUNT_QUERY, origin_domain, gtm_fit, prior_company_domain
            )
            total_leads = total_row["total"] if total_row else 0

            paginated_query = LEADS_QUERY + " LIMIT $4 OFFSET $5"
            rows = await conn.fetch(
                paginated_query, origin_domain, gtm_fit, prior_company_domain, limit, offset
            )

            summary_rows = await conn.fetch(
                PRIOR_COMPANIES_SUMMARY_QUERY, origin_domain, gtm_fit, prior_company_domain
            )

            # Collect unique current-company domains for batch lookups
            current_domains = list({r["current_company_domain"] for r in rows if r["current_company_domain"]})

            # Batch: technologies, meta ads, google ads
            tech_map: dict[str, list[str]] = {}
            meta_ads_map: dict[str, int] = {}
            google_ads_map: dict[str, int] = {}

            if current_domains:
                tech_rows = await conn.fetch(TECHNOLOGIES_QUERY, current_domains)
                for tr in tech_rows:
                    tech_map.setdefault(tr["domain"], []).append(tr["name"])

                meta_rows = await conn.fetch(META_ADS_COUNT_QUERY, current_domains)
                for mr in meta_rows:
                    meta_ads_map[mr["domain"]] = mr["cnt"]

                google_rows = await conn.fetch(GOOGLE_ADS_COUNT_QUERY, current_domains)
                for gr in google_rows:
                    google_ads_map[gr["domain"]] = gr["cnt"]

        # Build response objects
        leads: list[Lead] = []
        for r in rows:
            domain = r["current_company_domain"]
            leads.append(Lead(
                person=PersonData(
                    full_name=r["full_name"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    linkedin_url=r["person_linkedin_url"],
                    headline=r["headline"],
                    location=r["location_name"],
                    picture_url=r["picture_url"],
                    matched_seniority=r["matched_seniority"],
                    matched_job_function=r["matched_job_function"],
                ),
                current_company=CurrentCompany(
                    name=r["current_company_name"],
                    domain=domain,
                    linkedin_url=r["current_company_linkedin_url"],
                    role=r["current_role"],
                    cleaned_job_title=r["current_role"],
                    firmographics=Firmographics(
                        industry=r["industry"],
                        employee_count=r["employee_count"],
                        size_range=r["size_range"],
                        founded_year=r["founded_year"],
                        country=r["country"],
                        city=r["city"],
                        state=r["state"],
                        description=r["company_description"],
                    ) if r["industry"] or r["employee_count"] else None,
                    storeleads=StoreleadsData(
                        platform=r["platform"],
                        estimated_sales_yearly=float(r["estimated_sales_yearly"]) if r["estimated_sales_yearly"] else None,
                        product_count=r["product_count"],
                        rank=r["storeleads_rank"],
                        technologies=tech_map.get(domain),
                    ) if r["platform"] or r["storeleads_rank"] else None,
                    ads=AdsData(
                        meta_ads_count=meta_ads_map.get(domain, 0),
                        google_ads_count=google_ads_map.get(domain, 0),
                    ),
                ),
                prior_company=PriorCompany(
                    name=r["prior_company_name"],
                    domain=r["prior_company_domain"],
                    linkedin_url=r["prior_company_linkedin_url"],
                    role=r["prior_role"],
                    start_date=_str_or_none(r["prior_start_date"]),
                    end_date=_str_or_none(r["prior_end_date"]),
                    gtm_fit=r["gtm_fit"],
                    gtm_fit_reason=r["gtm_fit_reason"],
                ),
            ))

        prior_companies_summary = [
            PriorCompanySummary(
                name=sr["name"],
                domain=sr["domain"],
                lead_count=sr["lead_count"],
            )
            for sr in summary_rows
        ]

        return AlumniGTMLeadsResponse(
            success=True,
            origin_company_domain=origin_domain,
            total_leads=total_leads,
            total_prior_companies=len(prior_companies_summary),
            leads=leads,
            prior_companies_summary=prior_companies_summary,
        )

    except Exception as e:
        return AlumniGTMLeadsResponse(
            success=False,
            error=str(e),
            origin_company_domain=origin_domain,
            total_leads=0,
            total_prior_companies=0,
            leads=[],
            prior_companies_summary=[],
        )
