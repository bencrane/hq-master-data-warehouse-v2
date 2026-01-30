"""
Signal: Promotion

Ingest endpoint for promotion signals.
Detects when a person gets promoted (title change within same company).

Endpoint: POST /ingest-signal-promotion
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.signal_promotion_v2 import extract_signal_promotion


class SignalPromotionRequest(BaseModel):
    # Client tracking (required)
    client_domain: str

    # Raw payload from Clay (entire object)
    raw_promotion_payload: dict

    # Promotion recency filter (setting from Clay)
    days_since_promotion: Optional[int] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_signal_promotion(request: SignalPromotionRequest) -> dict:
    """
    Ingest promotion signal payload.
    Stores raw payload, then extracts to extracted.signal_promotion table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        raw = request.raw_promotion_payload

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
            .from_("signal_promotion_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_signal_promotion(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            client_domain=request.client_domain,
            raw_payload=raw,
            days_since_promotion=request.days_since_promotion,
        )

        # Get some info for response
        full_profile = raw.get("fullProfile", {})
        new_titles = raw.get("newTitle", [])

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "person_name": full_profile.get("name"),
            "new_title": new_titles[0] if new_titles else None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
