"""
Company ICP Lookup Endpoint

Returns company ICP criteria for filtering leads.
Reads from core.icp_criteria first, falls back to extracted tables.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CompanyICPLookupRequest(BaseModel):
    """Request model for company ICP lookup."""
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_icp(request: CompanyICPLookupRequest) -> dict:
    """
    Lookup company ICP data by domain.
    Checks core.icp_criteria first, falls back to extracted tables.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Try core.icp_criteria first (unified table)
        criteria_result = (
            supabase.schema("core")
            .from_("icp_criteria")
            .select("*")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )

        if criteria_result.data:
            # Use unified criteria table
            data = criteria_result.data

            # Still need customer domains from company_customers
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

            return {
                "success": True,
                "domain": request.domain,
                "company_name": data.get("company_name"),
                "customer_domains": customer_domains,
                # Company filters
                "industries": data.get("industries"),
                "countries": data.get("countries"),
                "employee_ranges": data.get("employee_ranges"),
                "funding_stages": data.get("funding_stages"),
                # People filters
                "job_titles": data.get("job_titles"),
                "seniorities": data.get("seniorities"),
                "job_functions": data.get("job_functions"),
                # Value prop
                "value_proposition": data.get("value_proposition"),
                "core_benefit": data.get("core_benefit"),
                "target_customer": data.get("target_customer"),
                "key_differentiator": data.get("key_differentiator"),
            }

        # Fallback to extracted tables
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

        # Get ICP industries (normalized/matched)
        industries_result = (
            supabase.schema("extracted")
            .from_("icp_industries")
            .select("matched_industries")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        industries = None
        if industries_result.data:
            industries = industries_result.data.get("matched_industries")

        # Get ICP job titles (cleaned/normalized) - flatten into single list
        job_titles_result = (
            supabase.schema("extracted")
            .from_("icp_job_titles")
            .select("primary_titles, influencer_titles, extended_titles")
            .eq("domain", request.domain)
            .maybe_single()
            .execute()
        )
        job_titles = None
        if job_titles_result.data:
            primary = job_titles_result.data.get("primary_titles") or []
            influencer = job_titles_result.data.get("influencer_titles") or []
            extended = job_titles_result.data.get("extended_titles") or []
            job_titles = primary + influencer + extended

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
        core_benefit = None
        target_customer = None
        key_differentiator = None
        if value_prop_result.data:
            value_proposition = value_prop_result.data.get("value_proposition")
            core_benefit = value_prop_result.data.get("core_benefit")
            target_customer = value_prop_result.data.get("target_customer")
            key_differentiator = value_prop_result.data.get("key_differentiator")

        return {
            "success": True,
            "domain": request.domain,
            "company_name": company_name,
            "customer_domains": customer_domains,
            # Company filters
            "industries": industries,
            "countries": None,  # Not in extracted tables
            "employee_ranges": None,  # Not in extracted tables
            "funding_stages": None,  # Not in extracted tables
            # People filters
            "job_titles": job_titles,
            "seniorities": None,  # Not in extracted tables
            "job_functions": None,  # Not in extracted tables
            # Value prop
            "value_proposition": value_proposition,
            "core_benefit": core_benefit,
            "target_customer": target_customer,
            "key_differentiator": key_differentiator,
        }

    except Exception as e:
        import traceback
        return {"success": False, "domain": request.domain, "error": str(e), "traceback": traceback.format_exc()}
