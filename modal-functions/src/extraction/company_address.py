"""
Company Address Parsing - Extraction

Extracts and stores parsed company address data from AI response.
"""

from typing import Optional
from supabase import Client


def extract_company_address(
    supabase: Client,
    raw_payload_id: str,
    company_name: Optional[str],
    linkedin_url: Optional[str],
    linkedin_urn: Optional[str],
    domain: Optional[str],
    description: Optional[str],
    headcount: Optional[int],
    industries: Optional[str],
    registered_address_raw: Optional[str],
    city: Optional[str],
    state: Optional[str],
    country: Optional[str],
    has_city: bool,
    has_state: bool,
    has_country: bool,
) -> dict:
    """
    Stores extracted company address data in extracted.company_address.
    
    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_name: Company name (as provided)
        linkedin_url: LinkedIn company URL
        linkedin_urn: LinkedIn URN
        domain: Company domain (as provided)
        description: Company description
        headcount: Company headcount as integer
        industries: Company industries
        registered_address_raw: Original address string
        city: AI-parsed city
        state: AI-parsed state
        country: AI-parsed country
        has_city: Whether city was present
        has_state: Whether state was present
        has_country: Whether country was present
    
    Returns:
        dict with extracted_id
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_name": company_name,
        "linkedin_url": linkedin_url,
        "linkedin_urn": linkedin_urn,
        "domain": domain,
        "description": description,
        "headcount": headcount,
        "industries": industries,
        "registered_address_raw": registered_address_raw,
        "city": city,
        "state": state,
        "country": country,
        "has_city": has_city,
        "has_state": has_state,
        "has_country": has_country,
    }

    result = (
        supabase.schema("extracted")
        .from_("salesnav_scrapes_company_address")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
