"""
ICP Industries Ingest Endpoint

Ingests target ICP industries for a company, matches against canonical industries using GPT.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ICPIndustriesRequest(BaseModel):
    """Request model for ICP industries ingestion."""
    # Company context
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None

    # Raw payload from AI
    raw_target_icp_industries_payload: dict

    # Metadata
    workflow_slug: str = "icp-industries"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials"), modal.Secret.from_name("openai-secret")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_icp_industries(request: ICPIndustriesRequest) -> dict:
    """
    Ingest ICP industries for a company.

    1. Stores raw payload
    2. Extracts industries and matches to canonical industries using GPT
    3. Stores extracted/matched data
    """
    from supabase import create_client
    from extraction.icp_industries import extract_and_match_icp_industries

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    openai_api_key = os.environ["OPENAI_API_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_record = {
            "company_name": request.company_name,
            "domain": request.domain,
            "company_linkedin_url": request.company_linkedin_url,
            "raw_payload": request.raw_target_icp_industries_payload,
            "workflow_slug": request.workflow_slug,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("icp_industries")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_id = raw_result.data[0]["id"]

        # Extract and match industries
        extraction_result = extract_and_match_icp_industries(
            supabase=supabase,
            openai_api_key=openai_api_key,
            raw_payload_id=raw_id,
            company_name=request.company_name,
            domain=request.domain,
            company_linkedin_url=request.company_linkedin_url,
            raw_payload=request.raw_target_icp_industries_payload,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "domain": request.domain,
            "raw_industries": extraction_result.get("raw_industries"),
            "matched_industries": extraction_result.get("matched_industries"),
            "matched_mapping": extraction_result.get("matched_mapping"),
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
