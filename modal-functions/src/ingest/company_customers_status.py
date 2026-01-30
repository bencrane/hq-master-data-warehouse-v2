"""
Company Customers Status Endpoint

Check if we have customers_of data for a given company domain.
Returns count and domain coverage stats.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CustomerStatusRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def get_company_customers_status(request: CustomerStatusRequest) -> dict:
    """
    Check customers_of status for a company domain.

    Returns:
    - has_customers: whether we have any customer data
    - total_customers: count of customers
    - customers_with_domain: count with domain populated
    - customers_without_domain: count without domain
    - domain_coverage_pct: percentage with domains
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get all customers for this domain
        result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("customer_name, customer_domain")
            .eq("origin_company_domain", request.domain)
            .execute()
        )

        customers = result.data
        total = len(customers)

        if total == 0:
            return {
                "success": True,
                "domain": request.domain,
                "has_customers": False,
                "total_customers": 0,
                "customers_with_domain": 0,
                "customers_without_domain": 0,
                "domain_coverage_pct": 0,
                "sample_customers": [],
            }

        # Count domain coverage
        with_domain = sum(1 for c in customers if c.get("customer_domain"))
        without_domain = total - with_domain
        coverage_pct = round((with_domain / total) * 100, 1) if total > 0 else 0

        # Sample customers (first 10)
        sample = [
            {
                "name": c.get("customer_name"),
                "domain": c.get("customer_domain"),
            }
            for c in customers[:10]
        ]

        return {
            "success": True,
            "domain": request.domain,
            "has_customers": True,
            "total_customers": total,
            "customers_with_domain": with_domain,
            "customers_without_domain": without_domain,
            "domain_coverage_pct": coverage_pct,
            "sample_customers": sample,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
