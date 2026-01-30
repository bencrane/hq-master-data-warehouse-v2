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
        # Get customers with company details
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("customer_name, customer_domain")
            .eq("origin_company_domain", request.domain)
            .not_.is_("customer_domain", "null")
            .execute()
        )

        customers = []
        if customers_result.data:
            customer_domains = [c["customer_domain"] for c in customers_result.data if c.get("customer_domain")]

            # Get enriched company data for each customer
            if customer_domains:
                companies_result = (
                    supabase.schema("core")
                    .from_("companies")
                    .select("domain, name, cleaned_name")
                    .in_("domain", customer_domains)
                    .execute()
                )

                company_map = {}
                if companies_result.data:
                    for c in companies_result.data:
                        company_map[c["domain"]] = c.get("cleaned_name") or c.get("name")

                # Get location and size data
                locations_result = (
                    supabase.schema("core")
                    .from_("company_locations")
                    .select("domain, country")
                    .in_("domain", customer_domains)
                    .execute()
                )

                location_map = {}
                if locations_result.data:
                    for loc in locations_result.data:
                        location_map[loc["domain"]] = loc.get("country")

                # Get employee range
                emp_result = (
                    supabase.schema("core")
                    .from_("company_employee_ranges")
                    .select("domain, employee_range")
                    .in_("domain", customer_domains)
                    .execute()
                )

                emp_map = {}
                if emp_result.data:
                    for e in emp_result.data:
                        emp_map[e["domain"]] = e.get("employee_range")

                # Get industry
                industry_result = (
                    supabase.schema("core")
                    .from_("company_industries")
                    .select("domain, industry")
                    .in_("domain", customer_domains)
                    .execute()
                )

                industry_map = {}
                if industry_result.data:
                    for i in industry_result.data:
                        industry_map[i["domain"]] = i.get("industry")

                # Build customer list
                for c in customers_result.data:
                    domain = c.get("customer_domain")
                    if domain:
                        customers.append({
                            "name": company_map.get(domain) or c.get("customer_name"),
                            "domain": domain,
                            "industry": industry_map.get(domain),
                            "size": emp_map.get(domain),
                            "country": location_map.get(domain),
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
