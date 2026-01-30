"""
Signal: Job Posting

Ingest endpoint for job posting signals.
Detects new job postings at monitored companies.

Endpoint: POST /ingest-signal-job-posting
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any

from config import app, image
from extraction.signal_job_posting_v2 import extract_signal_job_posting


class SignalJobPostingRequest(BaseModel):
    # Client tracking (required)
    client_domain: str

    # Raw payload from Clay (entire object)
    raw_job_post_data_payload: dict

    # Job posting recency filter (settings from Clay)
    min_days_since_job_posting: Optional[int] = None
    max_days_since_job_posting: Optional[int] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_signal_job_posting(request: SignalJobPostingRequest) -> dict:
    """
    Ingest job posting signal payload.
    Stores raw payload, then extracts to extracted.signal_job_posting table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        raw = request.raw_job_post_data_payload

        # Extract origin info if present
        origin = raw.get("origin", {})

        # Store raw payload
        raw_record = {
            "client_domain": request.client_domain,
            "origin_table_id": origin.get("tableId"),
            "origin_record_id": origin.get("recordId"),
            "raw_payload": raw,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("signal_job_posting_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract jobPostData for normalized storage
        job_post_data = raw.get("jobPostData", {})
        is_initial_check = raw.get("isInitialCheck", False)

        extraction_result = extract_signal_job_posting(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            client_domain=request.client_domain,
            job_post_data=job_post_data,
            is_initial_check=is_initial_check,
            min_days_since_job_posting=request.min_days_since_job_posting,
            max_days_since_job_posting=request.max_days_since_job_posting,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "company_domain": job_post_data.get("domain"),
            "job_title": job_post_data.get("title"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
