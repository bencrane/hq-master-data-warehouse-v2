"""
Clay Signal: Promotion

Ingest endpoint for Clay's "Promotion" signal.
Detects when a person receives a promotion.

Signal Type: Person-level
Required Input: person_linkedin_url
Output: confidence, previous_title, new_title, start_date_with_new_title
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.signal_promotion import extract_promotion_signal


class PromotionSignalRequest(BaseModel):
    # Input field
    person_linkedin_url: str
    
    # Raw payloads
    promotion_event_raw_payload: Optional[dict] = None
    person_record_raw_payload: Optional[dict] = None
    
    # Flattened fields from Clay
    confidence: Optional[int] = None
    previous_title: Optional[str] = None
    new_title: Optional[str] = None
    start_date_with_new_title: Optional[str] = None
    
    # Threshold setting (manually entered, e.g. 90 for 3 months)
    lookback_threshold_days: Optional[int] = None
    
    # Signal metadata
    signal_slug: str = "clay-promotion"
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_signal_promotion(request: PromotionSignalRequest) -> dict:
    """
    Ingest Clay "Promotion" signal payload.
    Stores raw payload, then extracts to extracted.clay_promotion table.
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
            "previous_title": request.previous_title,
            "new_title": request.new_title,
            "start_date_with_new_title": request.start_date_with_new_title,
        }

        # Store raw payload
        raw_record = {
            "person_linkedin_profile_url": request.person_linkedin_url,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "promotion_event_raw_payload": request.promotion_event_raw_payload,
            "person_record_raw_payload": request.person_record_raw_payload,
            "raw_event_payload": raw_event_payload,
            "lookback_threshold_days": request.lookback_threshold_days,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_promotion_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_promotion_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            person_linkedin_url=request.person_linkedin_url,
            confidence=request.confidence,
            previous_title=request.previous_title,
            new_title=request.new_title,
            start_date_with_new_title=request.start_date_with_new_title,
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
