"""
GTM Dashboard Lookup

Returns all data needed for a GTM dashboard for a given seller domain:
- Company customers
- Alumni leads with firmographics and GTM briefs
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List, Any

from config import app, image


class GTMDashboardRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    timeout=60,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_gtm_dashboard(request: GTMDashboardRequest) -> dict:
    """
    Get all GTM dashboard data for a seller domain.

    Returns:
        - customers: list of company customers
        - alumni_leads: list of alumni leads with firmographics and GTM briefs
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.domain.lower().strip()

        # 1. Get company customers
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("id, origin_company_domain, origin_company_name, customer_name, customer_domain, case_study_url, has_case_study, source, created_at")
            .eq("origin_company_domain", domain)
            .execute()
        )
        customers = customers_result.data or []

        # 2. Get alumni leads
        alumni_result = (
            supabase.schema("public")
            .from_("alumni_leads")
            .select("id, lead_name, lead_title, company_name, company_domain, priority, past_employer_name, past_employer_domain, past_job_title, target_client_name, target_client_domain, target_client_slug, person_linkedin_url, start_date, company_linkedin_url, created_at")
            .eq("target_client_domain", domain)
            .order("priority")
            .execute()
        )
        alumni_leads = alumni_result.data or []

        if not alumni_leads:
            return {
                "success": True,
                "domain": domain,
                "customers": customers,
                "customer_count": len(customers),
                "alumni_leads": [],
                "alumni_lead_count": 0,
            }

        # 3. Get unique company domains and linkedin urls for batch lookups
        company_domains = list(set(
            lead.get("company_domain") for lead in alumni_leads
            if lead.get("company_domain")
        ))
        linkedin_urls = list(set(
            lead.get("person_linkedin_url") for lead in alumni_leads
            if lead.get("person_linkedin_url")
        ))

        # 4. Batch fetch firmographics
        firmographics_map = {}
        if company_domains:
            firmo_result = (
                supabase.schema("extracted")
                .from_("company_firmographics")
                .select("company_domain, linkedin_url, name, description, website, logo_url, company_type, industry, founded_year, size_range, employee_count, follower_count, country, locality, city, state, matched_industry, matched_city, matched_state, matched_country")
                .in_("company_domain", company_domains)
                .execute()
            )
            if firmo_result.data:
                firmographics_map = {
                    f["company_domain"]: f for f in firmo_result.data
                }

        # 5. Batch fetch GTM briefs
        gtm_briefs_map = {}
        if linkedin_urls:
            gtm_result = (
                supabase.schema("public")
                .from_("gtm_briefs")
                .select("person_linkedin_url, overview, market_position, relevance_and_readiness, recommended_approach, takeaway, created_at")
                .in_("person_linkedin_url", linkedin_urls)
                .execute()
            )
            if gtm_result.data:
                gtm_briefs_map = {
                    g["person_linkedin_url"]: g for g in gtm_result.data
                }

        # 6. Merge data
        enriched_leads = []
        for lead in alumni_leads:
            company_domain = lead.get("company_domain")
            linkedin_url = lead.get("person_linkedin_url")

            firmographics = firmographics_map.get(company_domain) if company_domain else None
            gtm_brief = gtm_briefs_map.get(linkedin_url) if linkedin_url else None

            enriched_leads.append({
                **lead,
                "has_firmographics": firmographics is not None,
                "company_firmographics": firmographics,
                "has_gtm_brief": gtm_brief is not None,
                "gtm_brief": gtm_brief,
            })

        return {
            "success": True,
            "domain": domain,
            "customers": customers,
            "customer_count": len(customers),
            "alumni_leads": enriched_leads,
            "alumni_lead_count": len(enriched_leads),
            "leads_with_firmographics": sum(1 for l in enriched_leads if l["has_firmographics"]),
            "leads_with_gtm_brief": sum(1 for l in enriched_leads if l["has_gtm_brief"]),
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "domain": request.domain,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
