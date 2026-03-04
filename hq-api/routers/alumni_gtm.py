"""
AlumniGTM Leads Router

Returns qualified leads for AlumniGTM - people who previously worked at a client's
customers and now hold buying authority at new companies.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from db import core, extracted, get_pool

router = APIRouter(prefix="/v1/alumni-gtm", tags=["alumni-gtm"])


def row_to_dict(row):
    """Convert asyncpg Record to dict, converting UUIDs and dates to strings."""
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'hex'):  # UUID
            d[k] = str(v)
        elif hasattr(v, 'isoformat'):  # date/datetime
            d[k] = v.isoformat()
    return d


# Response models
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
    meta_ads_count: Optional[int] = None
    google_ads_count: Optional[int] = None


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


@router.get("/leads", response_model=AlumniGTMLeadsResponse)
async def get_alumni_gtm_leads(
    origin_company_domain: str = Query(..., description="The client's domain (e.g. nostra.ai)")
):
    """
    Get AlumniGTM leads for an origin company.
    Returns people who previously worked at the client's customers
    and now hold positions at new companies.
    """
    origin_domain = origin_company_domain.lower().strip()

    try:
        # Get people_targets
        people_targets_result = (
            core()
            .from_("people_targets")
            .select("id, full_name, first_name, last_name, person_linkedin_url, cleaned_job_title, company_name, domain, company_linkedin_url")
            .execute()
        )

        # Get company_targets for this origin
        company_targets_result = (
            core()
            .from_("company_targets")
            .select("*")
            .eq("origin_company_domain", origin_domain)
            .execute()
        )

        # Build lookup dict for company_targets by target_company_domain
        company_targets_by_domain = {}
        for ct in company_targets_result.data or []:
            company_targets_by_domain[ct["target_company_domain"]] = ct

        # Filter people_targets to only those with matching company_targets
        matching_people = []
        for pt in people_targets_result.data or []:
            if pt.get("domain") in company_targets_by_domain:
                matching_people.append(pt)

        total_leads = len(matching_people)

        # Get unique domains for batch lookups
        current_domains = list(set(p.get("domain") for p in matching_people if p.get("domain")))
        linkedin_urls = list(set(p.get("person_linkedin_url") for p in matching_people if p.get("person_linkedin_url")))

        # Batch fetch person profiles
        person_profiles = {}
        if linkedin_urls:
            pp_result = (
                extracted()
                .from_("person_profile")
                .select("linkedin_url, headline, location_name, picture_url, matched_seniority, matched_job_function")
                .in_("linkedin_url", linkedin_urls)
                .execute()
            )
            for pp in pp_result.data or []:
                person_profiles[pp["linkedin_url"]] = pp

        # Batch fetch company firmographics
        firmographics = {}
        if current_domains:
            cf_result = (
                extracted()
                .from_("company_firmographics")
                .select("company_domain, industry, employee_count, size_range, founded_year, country, city, state, description")
                .in_("company_domain", current_domains)
                .execute()
            )
            for cf in cf_result.data or []:
                firmographics[cf["company_domain"]] = cf

        # Batch fetch storeleads
        storeleads_data = {}
        if current_domains:
            sl_result = (
                extracted()
                .from_("storeleads_company")
                .select("domain, platform, estimated_sales_yearly, product_count, rank")
                .in_("domain", current_domains)
                .execute()
            )
            for sl in sl_result.data or []:
                storeleads_data[sl["domain"]] = sl

        # Batch fetch technologies
        technologies_by_domain = {}
        if current_domains:
            tech_result = (
                extracted()
                .from_("storeleads_technology")
                .select("domain, name")
                .in_("domain", current_domains)
                .execute()
            )
            for tech in tech_result.data or []:
                domain = tech["domain"]
                if domain not in technologies_by_domain:
                    technologies_by_domain[domain] = []
                technologies_by_domain[domain].append(tech["name"])

        # Batch fetch work history for prior roles
        work_history = {}
        if linkedin_urls:
            prior_domains = list(company_targets_by_domain.keys())
            if prior_domains:
                wh_result = (
                    core()
                    .from_("person_work_history")
                    .select("linkedin_url, company_domain, title, start_date, end_date")
                    .in_("linkedin_url", linkedin_urls)
                    .in_("company_domain", prior_domains)
                    .execute()
                )
                for wh in wh_result.data or []:
                    key = f"{wh['linkedin_url']}|{wh['company_domain']}"
                    work_history[key] = wh

        # Batch fetch ad counts
        meta_ads_counts = {}
        google_ads_counts = {}
        if current_domains:
            for domain in current_domains:
                meta_result = (
                    extracted()
                    .from_("company_meta_ads")
                    .select("id", count="exact")
                    .eq("domain", domain)
                    .execute()
                )
                meta_ads_counts[domain] = meta_result.count or 0

                google_result = (
                    extracted()
                    .from_("company_google_ads")
                    .select("id", count="exact")
                    .eq("domain", domain)
                    .execute()
                )
                google_ads_counts[domain] = google_result.count or 0

        # Build leads response
        leads = []
        prior_companies_count = {}

        for pt in matching_people:
            domain = pt.get("domain")
            linkedin_url = pt.get("person_linkedin_url")
            ct = company_targets_by_domain.get(domain, {})
            prior_domain = ct.get("target_company_domain")

            # Get work history for prior role
            wh_key = f"{linkedin_url}|{prior_domain}" if linkedin_url and prior_domain else None
            wh = work_history.get(wh_key, {})

            # Get person profile
            pp = person_profiles.get(linkedin_url, {})

            # Get firmographics
            cf = firmographics.get(domain, {})

            # Get storeleads
            sl = storeleads_data.get(domain, {})

            # Get technologies
            techs = technologies_by_domain.get(domain, [])

            lead = Lead(
                person=PersonData(
                    full_name=pt.get("full_name"),
                    first_name=pt.get("first_name"),
                    last_name=pt.get("last_name"),
                    linkedin_url=linkedin_url,
                    headline=pp.get("headline"),
                    location=pp.get("location_name"),
                    picture_url=pp.get("picture_url"),
                    matched_seniority=pp.get("matched_seniority"),
                    matched_job_function=pp.get("matched_job_function"),
                ),
                current_company=CurrentCompany(
                    name=pt.get("company_name"),
                    domain=domain,
                    linkedin_url=pt.get("company_linkedin_url"),
                    role=pt.get("cleaned_job_title"),
                    cleaned_job_title=pt.get("cleaned_job_title"),
                    firmographics=Firmographics(
                        industry=cf.get("industry"),
                        employee_count=cf.get("employee_count"),
                        size_range=cf.get("size_range"),
                        founded_year=cf.get("founded_year"),
                        country=cf.get("country"),
                        city=cf.get("city"),
                        state=cf.get("state"),
                        description=cf.get("description"),
                    ) if cf else None,
                    storeleads=StoreleadsData(
                        platform=sl.get("platform"),
                        estimated_sales_yearly=float(sl["estimated_sales_yearly"]) if sl.get("estimated_sales_yearly") else None,
                        product_count=sl.get("product_count"),
                        rank=sl.get("rank"),
                        technologies=techs if techs else None,
                    ) if sl else None,
                    ads=AdsData(
                        meta_ads_count=meta_ads_counts.get(domain, 0),
                        google_ads_count=google_ads_counts.get(domain, 0),
                    ),
                ),
                prior_company=PriorCompany(
                    name=ct.get("target_company_name"),
                    domain=prior_domain,
                    linkedin_url=ct.get("target_company_linkedin_url"),
                    role=wh.get("title"),
                    start_date=str(wh["start_date"]) if wh.get("start_date") else None,
                    end_date=str(wh["end_date"]) if wh.get("end_date") else None,
                    gtm_fit=ct.get("gtm_fit"),
                    gtm_fit_reason=ct.get("reason"),
                ),
            )
            leads.append(lead)

            # Count for prior companies summary
            if prior_domain:
                if prior_domain not in prior_companies_count:
                    prior_companies_count[prior_domain] = {
                        "name": ct.get("target_company_name"),
                        "domain": prior_domain,
                        "count": 0
                    }
                prior_companies_count[prior_domain]["count"] += 1

        # Build prior companies summary
        prior_companies_summary = [
            PriorCompanySummary(
                name=v["name"],
                domain=v["domain"],
                lead_count=v["count"]
            )
            for v in sorted(prior_companies_count.values(), key=lambda x: -x["count"])
        ]

        return AlumniGTMLeadsResponse(
            success=True,
            origin_company_domain=origin_domain,
            total_leads=total_leads,
            total_prior_companies=len(prior_companies_count),
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
