"""
Company Customers Lookup Endpoint

Returns customer companies for a given domain.
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
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("origin_company_name, origin_company_domain, customer_name, customer_domain")
            .eq("origin_company_domain", request.domain)
            .execute()
        )

        customers = []
        if customers_result.data:
            for c in customers_result.data:
                customers.append({
                    "origin_company_name": c.get("origin_company_name"),
                    "origin_company_domain": c.get("origin_company_domain"),
                    "customer_name": c.get("customer_name"),
                    "customer_domain": c.get("customer_domain"),
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
