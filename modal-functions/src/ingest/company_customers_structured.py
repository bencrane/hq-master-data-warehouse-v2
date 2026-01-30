"""
Company Customers Structured Ingest Endpoint

Receives webhooks from Clay tables containing structured customer output
where customers is an array of objects with url, companyName, hasCaseStudy.

Expected payload from Clay:
{
  "origin_company_domain": "example.com",
  "origin_company_name": "Example Inc",
  "origin_company_linkedin_url": "https://linkedin.com/company/example",
  "claygent_output": {
    "customers": [
      {"url": "https://...", "companyName": "Customer1", "hasCaseStudy": true},
      {"url": "https://...", "companyName": "Customer2", "hasCaseStudy": false}
    ],
    "reasoning": "...",
    "confidence": "high",
    "stepsTaken": ["url1", "url2"]
  }
}
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from config import app, image


class CustomerItem(BaseModel):
    url: Optional[str] = None
    companyName: Optional[str] = None
    hasCaseStudy: Optional[bool] = None


class StructuredClaygentOutput(BaseModel):
    customers: Optional[List[CustomerItem]] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[List[str]] = None


class CompanyCustomersStructuredRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    claygent_output: Optional[StructuredClaygentOutput] = None
    # Alternative field names Clay might use
    customers_claygent: Optional[StructuredClaygentOutput] = None
    batch_name: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_customers_structured(request: CompanyCustomersStructuredRequest) -> dict:
    """
    Ingest structured customers output from Clay webhook.
    Stores raw payload and extracts individual customer records.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    # Get claygent output from either field name
    claygent = request.claygent_output or request.customers_claygent

    if not claygent:
        return {
            "success": False,
            "error": "No claygent_output or customers_claygent found",
            "domain": request.origin_company_domain,
        }

    try:
        # Normalize domain
        domain = request.origin_company_domain.lower().strip()

        # Get customers list (may be empty or None)
        customers_list = claygent.customers or []

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("claygent_customers_structured_raw")
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

        # Insert each customer (may be 0 if empty)
        extracted_count = 0
        customer_names = []
        for customer in customers_list:
            if not customer.companyName:
                continue

            supabase.schema("extracted").from_("claygent_customers_structured").insert({
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
