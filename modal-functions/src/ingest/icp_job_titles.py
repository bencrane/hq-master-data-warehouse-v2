"""
ICP Job Titles Ingest Endpoint

Ingests target ICP job titles for a company, normalizes camelCase to human-readable format.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ICPJobTitlesRequest(BaseModel):
    """Request model for ICP job titles ingestion."""
    # Company context
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None

    # Raw payload from AI
    raw_target_icp_job_titles_payload: dict

    # Metadata
    workflow_slug: str = "icp-job-titles"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_icp_job_titles(request: ICPJobTitlesRequest) -> dict:
    """
    Ingest ICP job titles for a company.

    1. Stores raw payload
    2. Extracts and normalizes job titles (camelCase -> human-readable)
    3. Stores extracted data
    """
    from supabase import create_client
    from extraction.icp_job_titles import extract_icp_job_titles

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_record = {
            "company_name": request.company_name,
            "domain": request.domain,
            "company_linkedin_url": request.company_linkedin_url,
            "raw_payload": request.raw_target_icp_job_titles_payload,
            "workflow_slug": request.workflow_slug,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("icp_job_titles")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_id = raw_result.data[0]["id"]

        # Extract and normalize job titles
        extraction_result = extract_icp_job_titles(
            supabase=supabase,
            raw_payload_id=raw_id,
            company_name=request.company_name,
            domain=request.domain,
            company_linkedin_url=request.company_linkedin_url,
            raw_payload=request.raw_target_icp_job_titles_payload,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "domain": request.domain,
            "primary_titles": extraction_result.get("primary_titles"),
            "influencer_titles": extraction_result.get("influencer_titles"),
            "extended_titles": extraction_result.get("extended_titles"),
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
