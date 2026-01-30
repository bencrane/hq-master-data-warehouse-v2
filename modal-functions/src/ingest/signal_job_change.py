"""
Clay Signal: Job Change

Ingest endpoint for Clay's "Job Change" signal.
Detects when a person changes jobs.

Signal Type: Person-level
Required Input: person_linkedin_url
Output: confidence, previous_company_linkedin_url, new_company_*, start_date_at_new_job
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.signal_job_change import extract_job_change_signal


class JobChangeSignalRequest(BaseModel):
    # Input field
    person_linkedin_url: str
    
    # Raw payloads
    job_change_event_raw_payload: Optional[dict] = None
    person_record_raw_payload: Optional[dict] = None
    
    # Flattened fields from Clay (arrays come as comma-separated strings)
    confidence: Optional[int] = None
    previous_company_linkedin_url: Optional[str] = None
    new_company_linkedin_url: Optional[str] = None
    new_company_domain: Optional[str] = None
    new_company_name: Optional[str] = None
    start_date_at_new_job: Optional[str] = None
    started_within_threshold: Optional[bool] = None
    
    # Threshold setting (manually entered, e.g. 90 for 3 months)
    lookback_threshold_days: Optional[int] = None
    
    # Signal metadata
    signal_slug: str = "clay-job-change"
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_signal_job_change(request: JobChangeSignalRequest) -> dict:
    """
    Ingest Clay "Job Change" signal payload.
    Stores raw payload, then extracts to extracted.clay_job_change table.
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

        # Build raw event payload from flattened fields
        raw_event_payload = {
            "confidence": request.confidence,
            "previous_company_linkedin_url": request.previous_company_linkedin_url,
            "new_company_linkedin_url": request.new_company_linkedin_url,
            "new_company_domain": request.new_company_domain,
            "new_company_name": request.new_company_name,
            "start_date_at_new_job": request.start_date_at_new_job,
            "started_within_threshold": request.started_within_threshold,
        }

        # Store raw payload
        raw_record = {
            "person_linkedin_profile_url": request.person_linkedin_url,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "job_change_event_raw_payload": request.job_change_event_raw_payload,
            "person_record_raw_payload": request.person_record_raw_payload,
            "raw_event_payload": raw_event_payload,
            "lookback_threshold_days": request.lookback_threshold_days,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_job_change_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_job_change_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            person_linkedin_url=request.person_linkedin_url,
            confidence=request.confidence,
            previous_company_linkedin_url=request.previous_company_linkedin_url,
            new_company_linkedin_url=request.new_company_linkedin_url,
            new_company_domain=request.new_company_domain,
            new_company_name=request.new_company_name,
            start_date_at_new_job=request.start_date_at_new_job,
            started_within_threshold=request.started_within_threshold,
            lookback_threshold_days=request.lookback_threshold_days,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "person_linkedin_url": request.person_linkedin_url,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
