"""
Clay Signal: Job Posting

Ingest endpoint for Clay's "Job Posting" signal.
Detects new job postings at monitored companies.

Signal Type: Company-level
Required Input: company_linkedin_url
Output: company_name, job_title, location, company_domain, job_linkedin_url, post_on
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any

from config import app, image
from extraction.signal_job_posting import extract_job_posting_signal


class JobPostingSignalRequest(BaseModel):
    # Input fields (required)
    company_linkedin_url: str
    
    # Company record payload (full object from Clay)
    company_record_raw_payload: Optional[Any] = None
    
    # Clay output fields (flattened)
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    company_domain: Optional[str] = None
    job_linkedin_url: Optional[str] = None
    post_on: Optional[str] = None
    
    # Signal metadata
    signal_slug: str = "clay-job-posting"
    
    # Traceability
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_signal_job_posting(request: JobPostingSignalRequest) -> dict:
    """
    Ingest Clay "Job Posting" signal payload.
    Stores raw payload, then extracts to extracted.clay_job_posting table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up signal in registry
        signal_result = (
            supabase.schema("reference")
            .from_("signal_registry")
            .select("*")
            .eq("signal_slug", request.signal_slug)
            .single()
            .execute()
        )
        signal = signal_result.data

        if not signal:
            return {"success": False, "error": f"Signal '{request.signal_slug}' not found in registry"}

        if not signal.get("is_active", True):
            return {"success": False, "error": f"Signal '{request.signal_slug}' is not active"}

        # Store raw payload
        raw_record = {
            "company_linkedin_url": request.company_linkedin_url,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "company_record_raw_payload": request.company_record_raw_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_job_posting_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_job_posting_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            company_linkedin_url=request.company_linkedin_url,
            company_name=request.company_name,
            job_title=request.job_title,
            location=request.location,
            company_domain=request.company_domain,
            job_linkedin_url=request.job_linkedin_url,
            post_on=request.post_on,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "job_title": request.job_title,
            "company_name": request.company_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
