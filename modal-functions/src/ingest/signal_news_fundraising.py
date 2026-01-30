"""
Clay Signal: News & Fundraising

Ingest endpoint for Clay's "News & Fundraising" signal.
Detects news and fundraising events for monitored companies.

Signal Type: Company-level
Required Input: company_domain
Output: event, company_record, company_domains, news_url, news_title, publish_date, description
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any

from config import app, image
from extraction.signal_news_fundraising import extract_news_fundraising_signal


class NewsFundraisingSignalRequest(BaseModel):
    # Input fields (required)
    company_domain: str
    
    # Full Clay event payload (stored as-is)
    raw_event_payload: Optional[Any] = None
    
    # Clay output fields (flattened)
    news_url: Optional[str] = None
    news_title: Optional[str] = None
    description: Optional[str] = None
    
    # Signal metadata
    signal_slug: str = "clay-news-fundraising"
    
    # Traceability
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_signal_news_fundraising(request: NewsFundraisingSignalRequest) -> dict:
    """
    Ingest Clay "News & Fundraising" signal payload.
    Stores raw payload, then extracts to extracted.clay_news_fundraising table.
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
            "company_domain": request.company_domain,
            "signal_slug": request.signal_slug,
            "clay_table_url": request.clay_table_url,
            "raw_event_payload": request.raw_event_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_news_fundraising_payloads")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract normalized data
        extraction_result = extract_news_fundraising_signal(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            company_domain=request.company_domain,
            news_url=request.news_url,
            news_title=request.news_title,
            description=request.description,
            raw_event_payload=request.raw_event_payload,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "news_title": request.news_title,
            "news_url": request.news_url,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
