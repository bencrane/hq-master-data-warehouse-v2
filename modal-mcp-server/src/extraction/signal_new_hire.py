"""
Clay Signal: New Hire - Extraction

Extracts and normalizes New Hire signal data from raw payload.
"""

from typing import Optional
from supabase import Client


def extract_new_hire_signal(
    supabase: Client,
    raw_payload_id: str,
    company_domain: Optional[str],
    company_linkedin_url: Optional[str],
    company_name: Optional[str],
    person_linkedin_url: Optional[str],
) -> dict:
    """
    Extracts New Hire signal data and stores in extracted.clay_new_hire.
    
    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_domain: Company domain (input)
        company_linkedin_url: Company LinkedIn URL (input)
        company_name: Company name (Clay output)
        person_linkedin_url: New hire's LinkedIn URL (Clay output)
    
    Returns:
        dict with extracted_id
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_domain": company_domain,
        "company_linkedin_url": company_linkedin_url,
        "company_name": company_name,
        "person_linkedin_url": person_linkedin_url,
    }

    result = (
        supabase.schema("extracted")
        .from_("clay_new_hire")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
