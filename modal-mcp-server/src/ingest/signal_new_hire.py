"""
Clay Signal: New Hire

Ingest endpoint for Clay's "New Hire" signal.
Detects new hires at monitored companies.

Signal Type: Company-level
Required Input: company_domain OR company_linkedin_url
Output: company_name, person_linkedin_url
"""

import os
import modal
from pydantic import BaseModel, model_validator
from typing import Optional

from config import app, image
from extraction.signal_new_hire import extract_new_hire_signal


class NewHireSignalRequest(BaseModel):
    # Input fields (at least one required)
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    
    # Clay output fields
    company_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    
    # Signal metadata
    signal_slug: str = "clay-new-hire"
    
    # Traceability
    clay_table_url: Optional[str] = None
    
    @model_validator(mode="after")
    def check_identifier(self):
        if not self.company_domain and not self.company_linkedin_url:
            raise ValueError("Either company_domain or company_linkedin_url is required")
        return self


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_signal_new_hire(request: NewHireSignalRequest) -> dict:
    """
    Ingest Clay "New Hire" signal payload.
    Stores raw payload, then extracts to extracted.clay_new_hire table.
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

        # Build raw payload from all incoming fields
        raw_payload = {
            "company_name": request.company_name,
            "person_linkedin_url": request.person_linkedin_url,
        }

        # Store raw payload
        raw_record = {
            "company_domain": request.company_domain,
            "company_linkedin_url": request.company_linkedin_url,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "raw_payload": raw_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_new_hire_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_new_hire_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            company_domain=request.company_domain,
            company_linkedin_url=request.company_linkedin_url,
            company_name=request.company_name,
            person_linkedin_url=request.person_linkedin_url,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "company_name": request.company_name,
            "person_linkedin_url": request.person_linkedin_url,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
