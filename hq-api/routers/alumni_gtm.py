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


class MetaAd(BaseModel):
    ad_id: Optional[str] = None
    platform: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None
    page_name: Optional[str] = None
    ad_creative_body: Optional[str] = None
    ad_creative_link_title: Optional[str] = None
    ad_creative_link_description: Optional[str] = None
    landing_page_url: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None


class GoogleAd(BaseModel):
    creative_id: Optional[str] = None
    format: Optional[str] = None
    start_date: Optional[str] = None
    last_seen: Optional[str] = None
    advertiser_name: Optional[str] = None
    original_url: Optional[str] = None
    variant_content: Optional[str] = None


class AdsData(BaseModel):
    meta_ads_count: Optional[int] = 0
    google_ads_count: Optional[int] = 0
    meta_ads: Optional[List[MetaAd]] = None
    google_ads: Optional[List[GoogleAd]] = None


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
    firmographics: Optional[Firmographics] = None


class Lead(BaseModel):
    id: Optional[str] = None
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
    prior_company_domain: Optional[str] = None
    limit: Optional[int] = 500
    offset: Optional[int] = 0


# ---------------------------------------------------------------------------
# Main query — finds alumni leads:
#   people_targets (current company) ← person_work_history → company_customers (prior customer)
# DISTINCT ON deduplicates when person has multiple roles at the same customer.
# ---------------------------------------------------------------------------

LEADS_QUERY = """
SELECT DISTINCT ON (pt.person_linkedin_url, cc.customer_domain)
    pt.id AS people_target_id,
    pt.full_name,
    pt.first_name,
    pt.last_name,
    pt.person_linkedin_url,
    pt.cleaned_job_title  AS current_role,
    pt.company_name       AS current_company_name,
    pt.domain             AS current_company_domain,
    pt.company_linkedin_url AS current_company_linkedin_url,

    cc.customer_name      AS prior_company_name,
    cc.customer_domain    AS prior_company_domain,

    pwh.title             AS prior_role,
    pwh.start_date        AS prior_start_date,
    pwh.end_date          AS prior_end_date,

    ct.gtm_fit,
    ct.reason             AS gtm_fit_reason,

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
    cf.description        AS company_description,

    sl.platform,
    sl.estimated_sales_yearly,
    sl.product_count,
    sl.rank               AS storeleads_rank,

    cf2.industry          AS prior_industry,
    cf2.employee_count    AS prior_employee_count,
    cf2.size_range        AS prior_size_range,
    cf2.founded_year      AS prior_founded_year,
    cf2.country           AS prior_country,
    cf2.city              AS prior_city,
    cf2.state             AS prior_state,
    cf2.description       AS prior_company_description

FROM core.people_targets pt

JOIN core.person_work_history pwh
    ON pt.person_linkedin_url = pwh.linkedin_url
   AND pwh.is_current IS NOT TRUE

JOIN core.company_customers cc
    ON pwh.company_domain = cc.customer_domain
   AND cc.origin_company_domain = $1

LEFT JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1

LEFT JOIN extracted.person_profile pp
    ON pt.person_linkedin_url = pp.linkedin_url

LEFT JOIN extracted.company_firmographics cf
    ON pt.domain = cf.company_domain

LEFT JOIN extracted.storeleads_company sl
    ON pt.domain = sl.domain

LEFT JOIN extracted.company_firmographics cf2
    ON cc.customer_domain = cf2.company_domain

WHERE ct.gtm_fit = true
  AND pt.icp_fit = true
  AND ($2::text IS NULL OR cc.customer_domain = $2)

ORDER BY pt.person_linkedin_url, cc.customer_domain, pwh.end_date DESC NULLS FIRST
"""

COUNT_QUERY = """
SELECT count(DISTINCT (pt.person_linkedin_url, cc.customer_domain)) AS total
FROM core.people_targets pt
JOIN core.person_work_history pwh
    ON pt.person_linkedin_url = pwh.linkedin_url
   AND pwh.is_current IS NOT TRUE
JOIN core.company_customers cc
    ON pwh.company_domain = cc.customer_domain
   AND cc.origin_company_domain = $1
LEFT JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1
WHERE ct.gtm_fit = true
  AND pt.icp_fit = true
  AND ($2::text IS NULL OR cc.customer_domain = $2)
"""

TECHNOLOGIES_QUERY = """
SELECT domain, name
FROM extracted.storeleads_technology
WHERE domain = ANY($1::text[])
"""

META_ADS_QUERY = """
SELECT domain, ad_id, platform, start_date, end_date, status, page_name,
       ad_creative_body, ad_creative_link_title, ad_creative_link_description,
       landing_page_url, image_url, video_url
FROM extracted.company_meta_ads
WHERE domain = ANY($1::text[])
ORDER BY start_date DESC NULLS LAST
"""

GOOGLE_ADS_QUERY = """
SELECT domain, creative_id, format, start_date, last_seen,
       advertiser_name, original_url, variant_content
FROM extracted.company_google_ads
WHERE domain = ANY($1::text[])
ORDER BY last_seen DESC NULLS LAST
"""

PRIOR_COMPANIES_SUMMARY_QUERY = """
SELECT
    cc.customer_name  AS name,
    cc.customer_domain AS domain,
    count(DISTINCT pt.person_linkedin_url) AS lead_count
FROM core.people_targets pt
JOIN core.person_work_history pwh
    ON pt.person_linkedin_url = pwh.linkedin_url
   AND pwh.is_current IS NOT TRUE
JOIN core.company_customers cc
    ON pwh.company_domain = cc.customer_domain
   AND cc.origin_company_domain = $1
LEFT JOIN core.company_targets ct
    ON pt.domain = ct.target_company_domain
   AND ct.origin_company_domain = $1
WHERE ct.gtm_fit = true
  AND pt.icp_fit = true
  AND ($2::text IS NULL OR cc.customer_domain = $2)
GROUP BY cc.customer_domain, cc.customer_name
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
    prior_company_domain = request.prior_company_domain
    limit = min(request.limit or 500, 500)
    offset = request.offset or 0

    pool = get_pool()

    try:
        async with pool.acquire() as conn:
            total_row = await conn.fetchrow(
                COUNT_QUERY, origin_domain, prior_company_domain
            )
            total_leads = total_row["total"] if total_row else 0

            paginated_query = LEADS_QUERY + " LIMIT $3 OFFSET $4"
            rows = await conn.fetch(
                paginated_query, origin_domain, prior_company_domain, limit, offset
            )

            summary_rows = await conn.fetch(
                PRIOR_COMPANIES_SUMMARY_QUERY, origin_domain, prior_company_domain
            )

            # Collect unique current-company domains for batch lookups
            current_domains = list({r["current_company_domain"] for r in rows if r["current_company_domain"]})

            # Batch: technologies, meta ads, google ads
            tech_map: dict[str, list[str]] = {}
            meta_ads_map: dict[str, list[dict]] = {}
            google_ads_map: dict[str, list[dict]] = {}

            if current_domains:
                tech_rows = await conn.fetch(TECHNOLOGIES_QUERY, current_domains)
                for tr in tech_rows:
                    tech_map.setdefault(tr["domain"], []).append(tr["name"])

                meta_rows = await conn.fetch(META_ADS_QUERY, current_domains)
                for mr in meta_rows:
                    meta_ads_map.setdefault(mr["domain"], []).append(dict(mr))

                google_rows = await conn.fetch(GOOGLE_ADS_QUERY, current_domains)
                for gr in google_rows:
                    google_ads_map.setdefault(gr["domain"], []).append(dict(gr))

        # Build response objects
        leads: list[Lead] = []
        for r in rows:
            domain = r["current_company_domain"]
            leads.append(Lead(
                id=str(r["people_target_id"]),
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
                        meta_ads_count=len(meta_ads_map.get(domain, [])),
                        google_ads_count=len(google_ads_map.get(domain, [])),
                        meta_ads=[
                            MetaAd(
                                ad_id=a.get("ad_id"),
                                platform=a.get("platform"),
                                start_date=_str_or_none(a.get("start_date")),
                                end_date=_str_or_none(a.get("end_date")),
                                status=a.get("status"),
                                page_name=a.get("page_name"),
                                ad_creative_body=a.get("ad_creative_body"),
                                ad_creative_link_title=a.get("ad_creative_link_title"),
                                ad_creative_link_description=a.get("ad_creative_link_description"),
                                landing_page_url=a.get("landing_page_url"),
                                image_url=a.get("image_url"),
                                video_url=a.get("video_url"),
                            ) for a in meta_ads_map.get(domain, [])[:5]
                        ] or None,
                        google_ads=[
                            GoogleAd(
                                creative_id=a.get("creative_id"),
                                format=a.get("format"),
                                start_date=_str_or_none(a.get("start_date")),
                                last_seen=_str_or_none(a.get("last_seen")),
                                advertiser_name=a.get("advertiser_name"),
                                original_url=a.get("original_url"),
                                variant_content=a.get("variant_content"),
                            ) for a in google_ads_map.get(domain, [])[:5]
                        ] or None,
                    ),
                ),
                prior_company=PriorCompany(
                    name=r["prior_company_name"],
                    domain=r["prior_company_domain"],
                    role=r["prior_role"],
                    start_date=_str_or_none(r["prior_start_date"]),
                    end_date=_str_or_none(r["prior_end_date"]),
                    gtm_fit=r["gtm_fit"],
                    gtm_fit_reason=r["gtm_fit_reason"],
                    firmographics=Firmographics(
                        industry=r["prior_industry"],
                        employee_count=r["prior_employee_count"],
                        size_range=r["prior_size_range"],
                        founded_year=r["prior_founded_year"],
                        country=r["prior_country"],
                        city=r["prior_city"],
                        state=r["prior_state"],
                        description=r["prior_company_description"],
                    ) if r["prior_industry"] or r["prior_employee_count"] else None,
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
