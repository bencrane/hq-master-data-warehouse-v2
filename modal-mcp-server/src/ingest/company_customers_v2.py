"""
Company Customers V2 Ingest Endpoint

Receives webhooks from Clay tables containing structured customer output.
Handles empty customers arrays gracefully.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List

from config import app, image


class CustomerItem(BaseModel):
    url: Optional[str] = None
    companyName: Optional[str] = None
    hasCaseStudy: Optional[bool] = None


class ClaygentOutput(BaseModel):
    customers: Optional[List[CustomerItem]] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[List[str]] = None


class CompanyCustomersV2Request(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    claygent_output: Optional[ClaygentOutput] = None
    customers_claygent: Optional[ClaygentOutput] = None
    batch_name: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_customers_v2(request: CompanyCustomersV2Request) -> dict:
    """
    Ingest structured customers output from Clay webhook.
    Handles empty customers arrays - stores raw, extracts 0 customers.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    claygent = request.claygent_output or request.customers_claygent

    if not claygent:
        return {
            "success": False,
            "error": "No claygent_output or customers_claygent found",
            "domain": request.origin_company_domain,
        }

    try:
        domain = request.origin_company_domain.lower().strip()
        customers_list = claygent.customers or []

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("claygent_customers_v2_raw")
            .insert({
                "origin_company_domain": domain,
                "origin_company_name": request.origin_company_name,
                "origin_company_linkedin_url": request.origin_company_linkedin_url,
                "batch_name": request.batch_name,
                "confidence": claygent.confidence,
                "raw_payload": {
                    "customers": [
                        {"url": c.url, "companyName": c.companyName, "hasCaseStudy": c.hasCaseStudy}
                        for c in customers_list
                    ],
                    "reasoning": claygent.reasoning,
                    "confidence": claygent.confidence,
                    "stepsTaken": claygent.stepsTaken,
                },
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract customers (may be 0)
        extracted_count = 0
        customer_names = []
        for customer in customers_list:
            if not customer.companyName:
                continue

            supabase.schema("extracted").from_("claygent_customers_v2").insert({
                "raw_id": raw_id,
                "origin_company_domain": domain,
                "origin_company_name": request.origin_company_name,
                "customer_name": customer.companyName,
                "case_study_url": customer.url,
                "has_case_study": customer.hasCaseStudy,
                "confidence": claygent.confidence,
            }).execute()
            extracted_count += 1
            customer_names.append(customer.companyName)

        return {
            "success": True,
            "raw_id": str(raw_id),
            "domain": domain,
            "customers_extracted": extracted_count,
            "customer_names": customer_names,
            "confidence": claygent.confidence,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.origin_company_domain,
        }
