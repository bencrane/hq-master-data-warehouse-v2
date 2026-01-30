"""
Case Study Buyers Ingest

Ingests the payload from extract_case_study_buyer and stores in raw + extracted tables.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List, Any

from config import app, image
from extraction.case_study_champions import extract_case_study_buyers


class BuyerPerson(BaseModel):
    fullName: str
    jobTitle: Optional[str] = ""


class CaseStudyBuyersRequest(BaseModel):
    # Required: origin company info
    origin_company_name: str
    origin_company_domain: str
    case_study_url: Optional[str] = ""
    # From Gemini response
    customer_company_name: Optional[str] = ""
    customer_company_domain: Optional[str] = ""
    people: List[BuyerPerson] = []
    # Optional Gemini metadata (ignored but accepted)
    success: Optional[bool] = None
    cost_usd: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_case_study_buyers(request: CaseStudyBuyersRequest) -> dict:
    """
    Ingest case study buyers payload.
    Stores raw payload, then extracts each person to flattened table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload
        raw_payload = {
            "customer_company_name": request.customer_company_name,
            "customer_company_domain": request.customer_company_domain,
            "people": [p.model_dump() for p in request.people],
            "cost_usd": request.cost_usd,
            "input_tokens": request.input_tokens,
            "output_tokens": request.output_tokens,
        }

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("case_study_buyers_payloads")
            .insert({
                "origin_company_name": request.origin_company_name,
                "origin_company_domain": request.origin_company_domain,
                "customer_company_name": request.customer_company_name,
                "customer_company_domain": request.customer_company_domain,
                "case_study_url": request.case_study_url,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract buyers (explode people array)
        buyer_count = extract_case_study_buyers(
            supabase,
            raw_id,
            request.origin_company_name,
            request.origin_company_domain,
            request.customer_company_name,
            request.customer_company_domain,
            request.case_study_url,
            [p.model_dump() for p in request.people],
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "buyer_count": buyer_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
