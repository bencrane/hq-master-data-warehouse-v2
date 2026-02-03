"""
Clay Signal: Job Posting

Ingest endpoint for Clay's "Job Posting" signal.
Detects new job postings at monitored companies.

Signal Type: Company-level
Required Input: company_linkedin_url
Output: company_name, job_title, location, company_domain, job_linkedin_url, posted_at, etc.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any

from config import app, image
from extraction.signal_job_posting import extract_job_posting_signal


class JobPostingSignalRequest(BaseModel):
    # Input fields (either or both)
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None

    # Raw payload from Clay (entire object with jobPostData nested)
    raw_job_post_data_payload: Optional[dict] = None

    # Enriched fields (from Clay)
    cleaned_job_title: Optional[str] = None
    job_function: Optional[str] = None

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

        raw = request.raw_job_post_data_payload or {}

        # Resolve domain: prefer request.domain, fallback to jobPostData.domain
        job_post_data = raw.get("jobPostData", {})
        domain = request.domain or job_post_data.get("domain")
        if domain:
            domain = domain.lower().strip()

        # Require at least domain or company_linkedin_url
        if not domain and not request.company_linkedin_url:
            return {"success": False, "error": "Either domain or company_linkedin_url is required"}

        # Store raw payload
        raw_record = {
            "domain": domain,
            "company_linkedin_url": request.company_linkedin_url,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "raw_event_payload": raw,
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

        # Extract for normalized storage
        is_initial_check = raw.get("isInitialCheck", False)

        extraction_result = extract_job_posting_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            domain=domain,
            company_linkedin_url=request.company_linkedin_url,
            job_post_data=job_post_data,
            is_initial_check=is_initial_check,
            cleaned_job_title=request.cleaned_job_title,
            job_function=request.job_function,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "core_id": extraction_result.get("core_id"),
            "domain": domain,
            "job_title": job_post_data.get("title"),
            "cleaned_job_title": request.cleaned_job_title,
            "job_function": request.job_function,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
