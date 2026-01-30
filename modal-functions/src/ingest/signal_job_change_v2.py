"""
Signal: Job Change

Ingest endpoint for job change signals.
Detects when a person changes companies.

Endpoint: POST /ingest-signal-job-change
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.signal_job_change_v2 import extract_signal_job_change


class SignalJobChangeRequest(BaseModel):
    # Client tracking (required)
    client_domain: str

    # Raw payload from Clay (entire object)
    raw_job_change_payload: dict

    # Job change recency filter
    job_change_within_months: Optional[int] = None  # Threshold (e.g., 3, 6)
    started_role_within_window: Optional[bool] = None  # Boolean result from Clay


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_signal_job_change(request: SignalJobChangeRequest) -> dict:
    """
    Ingest job change signal payload.
    Stores raw payload, then extracts to extracted.signal_job_change table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        raw = request.raw_job_change_payload

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
            .from_("signal_job_change_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_signal_job_change(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            client_domain=request.client_domain,
            raw_payload=raw,
            job_change_within_months=request.job_change_within_months,
            started_role_within_window=request.started_role_within_window,
        )

        # Get some info for response
        full_profile = raw.get("fullProfile", {})
        latest_exp = full_profile.get("latest_experience", {})

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "person_name": full_profile.get("name"),
            "new_company_domain": latest_exp.get("company_domain"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
