"""
Lookup Similar Companies List Endpoint

Returns the list of similar companies for a given domain with LinkedIn URLs.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class SimilarCompaniesListRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_similar_companies_list(request: SimilarCompaniesListRequest) -> dict:
    """
    Lookup similar companies for a domain.
    Returns company name, domain, LinkedIn URL, and similarity score.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.domain.lower().strip()

        # Get similar companies
        result = (
            supabase.schema("core")
            .from_("company_similar_companies_preview")
            .select("company_name, company_domain, similarity_score")
            .eq("input_domain", domain)
            .order("similarity_score", desc=True)
            .execute()
        )

        if not result.data:
            return {
                "success": True,
                "domain": domain,
                "similar_count": 0,
                "similar_companies": [],
            }

        # Get unique domains for LinkedIn lookup
        company_domains = list(set(
            c.get("company_domain") for c in result.data
            if c.get("company_domain")
        ))

        # Fetch LinkedIn URLs from companies_full
        linkedin_map = {}
        if company_domains:
            linkedin_result = (
                supabase.schema("core")
                .from_("companies_full")
                .select("domain, linkedin_url")
                .in_("domain", company_domains)
                .execute()
            )
            if linkedin_result.data:
                linkedin_map = {
                    r["domain"]: r["linkedin_url"]
                    for r in linkedin_result.data
                    if r.get("linkedin_url")
                }

        # Build response
        similar_companies = []
        for c in result.data:
            company_domain = c.get("company_domain")
            similar_companies.append({
                "company_name": c.get("company_name"),
                "company_domain": company_domain,
                "company_linkedin_url": linkedin_map.get(company_domain) if company_domain else None,
                "similarity_score": c.get("similarity_score"),
            })

        return {
            "success": True,
            "domain": domain,
            "similar_count": len(similar_companies),
            "similar_companies": similar_companies,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "domain": request.domain,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
