"""
Clay Signal: News & Fundraising - Extraction

Extracts and normalizes News & Fundraising signal data from raw payload.
"""

from typing import Optional, Any
from supabase import Client


def extract_news_fundraising_signal(
    supabase: Client,
    raw_payload_id: str,
    company_domain: str,
    news_url: Optional[str],
    news_title: Optional[str],
    description: Optional[str],
    raw_event_payload: Optional[Any],
) -> dict:
    """
    Extracts News & Fundraising signal data and stores in extracted.clay_news_fundraising.
    
    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_domain: Company domain (input)
        news_url: Link to news article
        news_title: Headline
        description: Summary/description
        raw_event_payload: Full Clay event payload (for extracting publish_date)
    
    Returns:
        dict with extracted_id
    """
    # Extract publish_date from raw_event_payload.newsData.publishDate
    publish_date = None
    if raw_event_payload:
        try:
            news_data = raw_event_payload.get("newsData", {})
            publish_date = news_data.get("publishDate")  # Already in ISO format (YYYY-MM-DD)
        except Exception:
            pass

    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_domain": company_domain,
        "news_url": news_url,
        "news_title": news_title,
        "publish_date": publish_date,
        "description": description,
    }

    result = (
        supabase.schema("extracted")
        .from_("clay_news_fundraising")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
