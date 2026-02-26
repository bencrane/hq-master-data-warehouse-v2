"""
Lookup Past Customer Employment

Given a person's LinkedIn URL and a seller domain, find if they previously
worked at a company that was a customer of the seller.

Returns the past job title, company name, and domain if found.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class PastCustomerEmploymentRequest(BaseModel):
    linkedin_url: str
    seller_domain: str


@app.function(
    image=image,
    timeout=30,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_past_customer_employment(request: PastCustomerEmploymentRequest) -> dict:
    """
    Find if a person previously worked at a customer of the given seller.

    Args:
        linkedin_url: Person's LinkedIn URL
        seller_domain: Domain of the seller (e.g., withcoverage.com)

    Returns:
        past_job_title, past_company_name, past_company_domain if found
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Normalize inputs
        linkedin_url = request.linkedin_url.strip().rstrip("/")
        seller_domain = request.seller_domain.lower().strip()

        # 1. Get customers of the seller
        customers_result = (
            supabase.schema("core")
            .from_("company_customers")
            .select("customer_domain")
            .eq("domain", seller_domain)
            .execute()
        )

        if not customers_result.data:
            return {
                "success": True,
                "found": False,
                "linkedin_url": linkedin_url,
                "seller_domain": seller_domain,
                "past_job_title": None,
                "past_company_name": None,
                "past_company_domain": None,
                "message": "No customers found for seller",
            }

        customer_domains = [
            c["customer_domain"] for c in customers_result.data
            if c.get("customer_domain")
        ]

        if not customer_domains:
            return {
                "success": True,
                "found": False,
                "linkedin_url": linkedin_url,
                "seller_domain": seller_domain,
                "past_job_title": None,
                "past_company_name": None,
                "past_company_domain": None,
                "message": "No customer domains found",
            }

        # 2. Get person's past work history
        work_history_result = (
            supabase.schema("core")
            .from_("person_work_history")
            .select("raw_job_title, company_name, company_domain, start_date")
            .eq("person_linkedin_url", linkedin_url)
            .eq("is_current", False)
            .order("start_date", desc=True)
            .execute()
        )

        if not work_history_result.data:
            return {
                "success": True,
                "found": False,
                "linkedin_url": linkedin_url,
                "seller_domain": seller_domain,
                "past_job_title": None,
                "past_company_name": None,
                "past_company_domain": None,
                "message": "No past work history found for person",
            }

        # 3. Find intersection - past jobs at customer companies
        customer_domains_set = set(customer_domains)

        for job in work_history_result.data:
            job_domain = job.get("company_domain")
            if job_domain and job_domain in customer_domains_set:
                return {
                    "success": True,
                    "found": True,
                    "linkedin_url": linkedin_url,
                    "seller_domain": seller_domain,
                    "past_job_title": job.get("raw_job_title"),
                    "past_company_name": job.get("company_name"),
                    "past_company_domain": job_domain,
                }

        # No match found
        return {
            "success": True,
            "found": False,
            "linkedin_url": linkedin_url,
            "seller_domain": seller_domain,
            "past_job_title": None,
            "past_company_name": None,
            "past_company_domain": None,
        }

    except Exception as e:
        return {
            "success": False,
            "found": False,
            "linkedin_url": request.linkedin_url,
            "seller_domain": request.seller_domain,
            "error": str(e),
        }
