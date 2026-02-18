"""
Case Study Champions Lookup Endpoint

Returns champions (buyers/users featured in case studies) for a given vendor domain.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ChampionsLookupRequest(BaseModel):
    """Request model for champions lookup."""
    domain: str  # origin_company_domain (vendor domain)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_case_study_champions(request: ChampionsLookupRequest) -> dict:
    """
    Lookup case study champions by vendor domain.
    Returns champions featured in the vendor's case studies.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get champions for this vendor
        champions_result = (
            supabase.schema("core")
            .from_("case_study_champions")
            .select("full_name, job_title, company_name, company_domain, case_study_url, source")
            .eq("origin_company_domain", request.domain)
            .execute()
        )

        champions = []
        if champions_result.data:
            # Get unique company domains for LinkedIn URL lookup
            company_domains = list(set(
                c.get("company_domain") for c in champions_result.data
                if c.get("company_domain")
            ))

            # Fetch company LinkedIn URLs
            company_linkedin_map = {}
            if company_domains:
                linkedin_result = (
                    supabase.schema("core")
                    .from_("companies_full")
                    .select("domain, linkedin_url")
                    .in_("domain", company_domains)
                    .execute()
                )
                if linkedin_result.data:
                    company_linkedin_map = {
                        r["domain"]: r["linkedin_url"]
                        for r in linkedin_result.data
                        if r.get("linkedin_url")
                    }

            # Build response
            for c in champions_result.data:
                company_domain = c.get("company_domain")
                champions.append({
                    "full_name": c.get("full_name"),
                    "job_title": c.get("job_title"),
                    "company_name": c.get("company_name"),
                    "company_domain": company_domain,
                    "company_linkedin_url": company_linkedin_map.get(company_domain) if company_domain else None,
                    "case_study_url": c.get("case_study_url"),
                    "source": c.get("source"),
                })

        return {
            "success": True,
            "domain": request.domain,
            "champion_count": len(champions),
            "champions": champions,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "domain": request.domain,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
