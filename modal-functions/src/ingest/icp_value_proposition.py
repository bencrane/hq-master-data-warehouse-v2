"""
ICP Value Proposition Ingest Endpoint

Ingests core value proposition for a company.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ICPValuePropositionRequest(BaseModel):
    """Request model for ICP value proposition ingestion."""
    # Company context
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None

    # Raw payload from AI
    target_icp_value_prop_payload: dict

    # Metadata
    workflow_slug: str = "icp-value-proposition"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_icp_value_proposition(request: ICPValuePropositionRequest) -> dict:
    """
    Ingest ICP value proposition for a company.

    1. Stores raw payload
    2. Extracts value proposition fields
    3. Stores extracted data
    """
    from supabase import create_client
    from extraction.icp_value_proposition import extract_icp_value_proposition

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_record = {
            "company_name": request.company_name,
            "domain": request.domain,
            "company_linkedin_url": request.company_linkedin_url,
            "raw_payload": request.target_icp_value_prop_payload,
            "workflow_slug": request.workflow_slug,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("icp_value_proposition")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_id = raw_result.data[0]["id"]

        # Extract value proposition
        extraction_result = extract_icp_value_proposition(
            supabase=supabase,
            raw_payload_id=raw_id,
            company_name=request.company_name,
            domain=request.domain,
            company_linkedin_url=request.company_linkedin_url,
            raw_payload=request.target_icp_value_prop_payload,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "domain": request.domain,
            "value_proposition": extraction_result.get("value_proposition"),
            "core_benefit": extraction_result.get("core_benefit"),
            "target_customer": extraction_result.get("target_customer"),
            "key_differentiator": extraction_result.get("key_differentiator"),
            "confidence": extraction_result.get("confidence"),
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
