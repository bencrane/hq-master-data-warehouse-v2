"""
Company Customers Lookup Endpoint

Returns customer companies for a given domain, including customer LinkedIn URLs.
v2 - Uses core.companies_full for LinkedIn URLs.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CompanyCustomersLookupRequest(BaseModel):
    """Request model for company customers lookup."""
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_customers(request: CompanyCustomersLookupRequest) -> dict:
    """
    Lookup customer companies by domain.
    Includes customer LinkedIn URL if available.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get customers
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("origin_company_name, origin_company_domain, customer_name, customer_domain")
            .eq("origin_company_domain", request.domain)
            .execute()
        )

        customers = []
        if customers_result.data:
            # Get unique customer domains that are not null
            customer_domains = list(set(
                c.get("customer_domain") for c in customers_result.data
                if c.get("customer_domain")
            ))

            # Fetch LinkedIn URLs from companies_full
            linkedin_map = {}
            if customer_domains:
                linkedin_result = (
                    supabase.schema("core")
                    .from_("companies_full")
                    .select("domain, linkedin_url")
                    .in_("domain", customer_domains)
                    .execute()
                )
                if linkedin_result.data:
                    linkedin_map = {r["domain"]: r["linkedin_url"] for r in linkedin_result.data if r.get("linkedin_url")}

            # Build response with LinkedIn URLs
            for c in customers_result.data:
                customer_domain = c.get("customer_domain")
                customers.append({
                    "origin_company_name": c.get("origin_company_name"),
                    "origin_company_domain": c.get("origin_company_domain"),
                    "customer_name": c.get("customer_name"),
                    "customer_domain": customer_domain,
                    "customer_linkedin_url": linkedin_map.get(customer_domain) if customer_domain else None,
                })

        return {
            "success": True,
            "domain": request.domain,
            "customer_count": len(customers),
            "customers": customers,
        }

    except Exception as e:
        import traceback
        return {"success": False, "domain": request.domain, "error": str(e), "traceback": traceback.format_exc()}
