"""
Signal: Job Change - Extraction

Extracts and normalizes job change signal data from raw payload.
"""

from typing import Optional
from datetime import datetime
from supabase import Client


def extract_signal_job_change(
    supabase: Client,
    raw_payload_id: str,
    client_domain: str,
    raw_payload: dict,
    job_change_within_months: int = None,
    started_role_within_window: bool = None,
) -> dict:
    """
    Extracts job change signal data and stores in extracted.signal_job_change.

    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        client_domain: Client domain for multi-tenant tracking
        raw_payload: The full payload

    Returns:
        dict with extracted_id
    """
    # Get nested data
    full_profile = raw_payload.get("fullProfile", {})
    latest_exp = full_profile.get("latest_experience", {})

    # Parse new job start date
    new_job_start_date = None
    start_date_str = latest_exp.get("start_date")
    if start_date_str:
        try:
            new_job_start_date = datetime.fromisoformat(
                start_date_str.replace("Z", "+00:00")
            ).date().isoformat()
        except (ValueError, AttributeError):
            pass

    # Build extracted record
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "client_domain": client_domain,
        # Person info
        "person_name": full_profile.get("name"),
        "person_first_name": full_profile.get("first_name"),
        "person_last_name": full_profile.get("last_name"),
        "person_linkedin_url": full_profile.get("url"),
        "person_linkedin_slug": full_profile.get("slug"),
        "person_title": full_profile.get("title"),
        "person_headline": full_profile.get("headline"),
        "person_location": full_profile.get("location_name"),
        "person_country": full_profile.get("country"),
        # New company info
        "new_company_domain": latest_exp.get("company_domain"),
        "new_company_name": latest_exp.get("company"),
        "new_company_linkedin_url": latest_exp.get("url"),
        "new_job_title": latest_exp.get("title"),
        "new_job_start_date": new_job_start_date,
        "new_job_location": latest_exp.get("locality"),
        # Previous company
        "previous_company_linkedin_url": raw_payload.get("previousCompany"),
        # Confidence
        "confidence": raw_payload.get("confidence"),
        "reduced_confidence_reasons": raw_payload.get("reducedConfidenceReasons"),
        # Metadata
        "is_initial_check": raw_payload.get("isInitialCheck", False),
        # Job change recency
        "job_change_within_months": job_change_within_months,
        "started_role_within_window": started_role_within_window,
    }

    result = (
        supabase.schema("extracted")
        .from_("signal_job_change")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
