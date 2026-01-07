"""
Company Extraction Functions

Extract and flatten company data from raw payloads.
"""

from typing import Any, Optional
from datetime import datetime


def extract_company_firmographics(supabase, raw_payload_id: str, company_domain: str, payload: dict) -> Optional[str]:
    """
    Extract company firmographics from raw payload to extracted.company_firmographics.
    Upserts on company_domain.
    """
    # Get primary location
    locations = payload.get("locations", [])
    primary_location = None
    if locations:
        for loc in locations:
            if loc.get("is_primary"):
                primary_location = loc
                break
        if not primary_location:
            primary_location = locations[0]

    # Parse source_last_refresh
    source_last_refresh = None
    if payload.get("last_refresh"):
        try:
            source_last_refresh = payload["last_refresh"]
        except:
            pass

    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_domain": company_domain,
        "linkedin_url": payload.get("url"),
        "linkedin_slug": payload.get("slug"),
        "linkedin_org_id": payload.get("org_id"),
        "clay_company_id": payload.get("company_id"),
        "name": payload.get("name"),
        "description": payload.get("description"),
        "website": payload.get("website"),
        "logo_url": payload.get("logo_url"),
        "company_type": payload.get("type"),
        "industry": payload.get("industry"),
        "founded_year": payload.get("founded"),
        "size_range": payload.get("size"),
        "employee_count": payload.get("employee_count"),
        "follower_count": payload.get("follower_count"),
        "country": payload.get("country"),
        "locality": payload.get("locality"),
        "primary_location": primary_location,
        "all_locations": locations if locations else None,
        "specialties": payload.get("specialties"),
        "source_last_refresh": source_last_refresh,
    }

    # Upsert on company_domain
    result = (
        supabase.schema("extracted")
        .from_("company_firmographics")
        .upsert(extracted_data, on_conflict="company_domain")
        .execute()
    )

    return result.data[0]["id"] if result.data else None


def extract_find_companies(supabase, raw_payload_id: str, company_domain: str, payload: dict) -> Optional[str]:
    """
    Extract company discovery data from raw payload to extracted.company_discovery.
    Upserts on domain.
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "domain": company_domain,
        "name": payload.get("name"),
        "linkedin_url": payload.get("linkedin_url"),
        "linkedin_company_id": payload.get("linkedin_company_id"),
        "clay_company_id": payload.get("clay_company_id"),
        "size": payload.get("size"),
        "type": payload.get("type"),
        "country": payload.get("country"),
        "location": payload.get("location"),
        "industry": payload.get("industry"),
        "industries": payload.get("industries"),
        "description": payload.get("description"),
        "annual_revenue": payload.get("annual_revenue"),
        "total_funding_amount_range_usd": payload.get("total_funding_amount_range_usd"),
        "resolved_domain": payload.get("resolved_domain"),
        "derived_datapoints": payload.get("derived_datapoints"),
    }

    # Upsert on domain
    result = (
        supabase.schema("extracted")
        .from_("company_discovery")
        .upsert(extracted_data, on_conflict="domain")
        .execute()
    )

    return result.data[0]["id"] if result.data else None
