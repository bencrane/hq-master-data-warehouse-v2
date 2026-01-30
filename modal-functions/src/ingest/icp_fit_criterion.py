"""
ICP Fit Criterion Ingest Endpoint

Ingests primary fit criterion for a company.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ICPFitCriterionRequest(BaseModel):
    """Request model for ICP fit criterion ingestion."""
    # Company context
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None

    # Raw payload from AI
    raw_target_icp_fit_criterion_payload: dict

    # Metadata
    workflow_slug: str = "icp-fit-criterion"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_icp_fit_criterion(request: ICPFitCriterionRequest) -> dict:
    """
    Ingest ICP fit criterion for a company.

    1. Stores raw payload
    2. Extracts fit criterion fields
    3. Stores extracted data
    """
    from supabase import create_client
    from extraction.icp_fit_criterion import extract_icp_fit_criterion

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_record = {
            "company_name": request.company_name,
            "domain": request.domain,
            "company_linkedin_url": request.company_linkedin_url,
            "raw_payload": request.raw_target_icp_fit_criterion_payload,
            "workflow_slug": request.workflow_slug,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("icp_fit_criterion")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_id = raw_result.data[0]["id"]

        # Extract fit criterion
        extraction_result = extract_icp_fit_criterion(
            supabase=supabase,
            raw_payload_id=raw_id,
            company_name=request.company_name,
            domain=request.domain,
            company_linkedin_url=request.company_linkedin_url,
            raw_payload=request.raw_target_icp_fit_criterion_payload,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "domain": request.domain,
            "primary_criterion": extraction_result.get("primary_criterion"),
            "criterion_type": extraction_result.get("criterion_type"),
            "qualifying_signals": extraction_result.get("qualifying_signals"),
            "disqualifying_signals": extraction_result.get("disqualifying_signals"),
            "ideal_company_attributes": extraction_result.get("ideal_company_attributes"),
            "minimum_requirements": extraction_result.get("minimum_requirements"),
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
