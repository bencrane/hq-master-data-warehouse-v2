"""
Create Target Client View Endpoint

Auto-generates a saved view from ICP data for a given domain.
"""

import os
import re
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class CreateTargetClientViewRequest(BaseModel):
    """Request model for creating a target client view."""
    domain: str
    slug: Optional[str] = None  # Auto-generated if not provided


def generate_slug(name: str, domain: str) -> str:
    """Generate a URL-friendly slug from company name or domain."""
    base = name if name else domain.split('.')[0]
    # Lowercase, replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')
    return slug


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def create_target_client_view(request: CreateTargetClientViewRequest) -> dict:
    """
    Create a saved target client view from ICP data.

    1. Looks up company name, customer domains, ICP industries, job titles, value prop
    2. Assembles filters
    3. Saves to core.target_client_views
    4. Returns shareable slug
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get company name
        company_result = (
            supabase.schema("core")
            .from_("companies")
            .select("name, cleaned_name")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        company_name = None
        if company_result.data:
            company_name = company_result.data.get("cleaned_name") or company_result.data.get("name")

        # Get customer domains
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("customer_domain")
            .eq("origin_company_domain", request.domain)
            .not_.is_("customer_domain", "null")
            .execute()
        )
        customer_domains = []
        if customers_result.data:
            customer_domains = [c["customer_domain"] for c in customers_result.data if c.get("customer_domain")]

        # Get ICP industries (normalized)
        industries_result = (
            supabase.schema("extracted")
            .from_("icp_industries")
            .select("matched_industries")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        icp_industries = None
        if industries_result.data:
            icp_industries = industries_result.data.get("matched_industries")

        # Get ICP job titles (cleaned)
        job_titles_result = (
            supabase.schema("extracted")
            .from_("icp_job_titles")
            .select("primary_titles, influencer_titles, extended_titles")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        icp_job_titles = None
        if job_titles_result.data:
            # Combine all title types into one list
            primary = job_titles_result.data.get("primary_titles") or []
            influencer = job_titles_result.data.get("influencer_titles") or []
            extended = job_titles_result.data.get("extended_titles") or []
            icp_job_titles = primary + influencer + extended

        # Get value proposition
        value_prop_result = (
            supabase.schema("extracted")
            .from_("icp_value_proposition")
            .select("value_proposition, core_benefit, target_customer, key_differentiator")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        value_proposition = None
        if value_prop_result.data:
            value_proposition = value_prop_result.data.get("value_proposition")

        # Generate slug if not provided
        slug = request.slug if request.slug else generate_slug(company_name, request.domain)

        # Assemble filters
        filters = {
            "customer_domains": customer_domains,
            "icp_industries": icp_industries,
            "icp_job_titles": icp_job_titles,
        }

        # Upsert to target_client_views
        view_record = {
            "domain": request.domain,
            "name": company_name,
            "slug": slug,
            "filters": filters,
        }

        view_result = (
            supabase.schema("core")
            .from_("target_client_views")
            .upsert(view_record, on_conflict="domain")
            .execute()
        )

        view_id = view_result.data[0]["id"] if view_result.data else None

        return {
            "success": True,
            "view_id": view_id,
            "domain": request.domain,
            "company_name": company_name,
            "slug": slug,
            "shareable_url": f"/leads?view={slug}",
            "filters": filters,
            "value_proposition": value_proposition,
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
