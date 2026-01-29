"""
Company Customers Claygent Ingest Endpoint

Receives webhooks from Clay tables containing Claygent output
for company customers/testimonials scraping.

Expected payload from Clay:
{
  "origin_company_domain": "example.com",
  "origin_company_name": "Example Inc",
  "origin_company_linkedin_url": "https://linkedin.com/company/example",
  "claygent_output": {
    "result": "Customer1, Customer2, Customer3",
    "reasoning": "...",
    "confidence": "high",
    "stepsTaken": ["url1", "url2"]
  }
}
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

from config import app, image


class ClaygentOutput(BaseModel):
    result: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    stepsTaken: Optional[List[str]] = None


class CompanyCustomersClaygentRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    claygent_output: Optional[ClaygentOutput] = None
    # Alternative field names Clay might use
    customers_claygent: Optional[ClaygentOutput] = None
    batch_name: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_customers_claygent(request: CompanyCustomersClaygentRequest) -> dict:
    """
    Ingest Claygent customers output from Clay webhook.
    Stores raw payload and extracts individual customer names.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    # Get claygent output from either field name
    claygent = request.claygent_output or request.customers_claygent

    if not claygent or not claygent.result:
        return {
            "success": False,
            "error": "No claygent_output or customers_claygent with result found",
            "domain": request.origin_company_domain,
        }

    try:
        # Normalize domain
        domain = request.origin_company_domain.lower().strip()

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("claygent_customers_raw")
            .insert({
                "origin_company_domain": domain,
                "origin_company_name": request.origin_company_name,
                "origin_company_linkedin_url": request.origin_company_linkedin_url,
                "batch_name": request.batch_name,
                "confidence": claygent.confidence,
                "raw_payload": {
                    "result": claygent.result,
                    "reasoning": claygent.reasoning,
                    "confidence": claygent.confidence,
                    "stepsTaken": claygent.stepsTaken,
                },
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Parse comma-separated customer names
        customer_names = [name.strip() for name in claygent.result.split(",") if name.strip()]

        # Extract case study URLs from stepsTaken
        case_study_urls = claygent.stepsTaken or []

        # Insert each customer
        extracted_count = 0
        for customer_name in customer_names:
            # Check if any stepsTaken URL might be a case study for this customer
            case_study_url = None
            customer_lower = customer_name.lower().replace(" ", "-").replace(".", "")
            for url in case_study_urls:
                if customer_lower in url.lower() or "case-study" in url.lower() or "case_study" in url.lower():
                    case_study_url = url
                    break

            supabase.schema("extracted").from_("claygent_customers").insert({
                "raw_id": raw_id,
                "origin_company_domain": domain,
                "origin_company_name": request.origin_company_name,
                "customer_name": customer_name,
                "case_study_url": case_study_url,
                "confidence": claygent.confidence,
            }).execute()
            extracted_count += 1

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
