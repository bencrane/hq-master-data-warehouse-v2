"""
Company Mapping Functions

Maps extracted company data against lookup tables:
- Location → reference.location_parsed
- Industry → reference.industry_lookup
- Company Name → extracted.cleaned_company_names
"""

from typing import Optional
from supabase import Client


def map_company_discovery(
    supabase: Client,
    extracted_id: str,
    domain: str,
    location: Optional[str],
    industry: Optional[str],
    company_name: Optional[str],
) -> dict:
    """
    Map extracted company data against lookup tables and store in mapped.company_discovery.

    Args:
        supabase: Supabase client
        extracted_id: ID of the extracted.company_discovery record
        domain: Company domain
        location: Raw location string to match
        industry: Raw industry string to match
        company_name: Raw company name to match

    Returns:
        dict with matched values and status
    """
    # Initialize results
    matched_city = None
    matched_state = None
    matched_country = None
    location_match_source = None
    matched_industry = None
    matched_company_name = None

    # 1. Match location against reference.location_parsed
    if location:
        location_result = (
            supabase.schema("reference")
            .from_("location_parsed")
            .select("city, state, country, source")
            .eq("raw_location", location)
            .limit(1)
            .execute()
        )
        if location_result.data:
            match = location_result.data[0]
            matched_city = match.get("city")
            matched_state = match.get("state")
            matched_country = match.get("country")
            location_match_source = match.get("source")

    # 2. Match industry against reference.industry_lookup
    if industry:
        industry_result = (
            supabase.schema("reference")
            .from_("industry_lookup")
            .select("industry_cleaned")
            .eq("industry_raw", industry)
            .limit(1)
            .execute()
        )
        if industry_result.data:
            matched_industry = industry_result.data[0].get("industry_cleaned")

    # 3. Match company name against extracted.cleaned_company_names (by domain)
    if domain:
        name_result = (
            supabase.schema("extracted")
            .from_("cleaned_company_names")
            .select("cleaned_company_name")
            .eq("domain", domain)
            .limit(1)
            .execute()
        )
        if name_result.data:
            matched_company_name = name_result.data[0].get("cleaned_company_name")

    # 4. Upsert to mapped.company_discovery
    mapped_data = {
        "extracted_id": extracted_id,
        "domain": domain,
        "original_location": location,
        "original_industry": industry,
        "original_company_name": company_name,
        "matched_city": matched_city,
        "matched_state": matched_state,
        "matched_country": matched_country,
        "location_match_source": location_match_source,
        "matched_industry": matched_industry,
        "matched_company_name": matched_company_name,
    }

    result = (
        supabase.schema("mapped")
        .from_("company_discovery")
        .upsert(mapped_data, on_conflict="domain")
        .execute()
    )

    return {
        "mapped_id": result.data[0]["id"] if result.data else None,
        "matched_city": matched_city,
        "matched_state": matched_state,
        "matched_country": matched_country,
        "matched_industry": matched_industry,
        "matched_company_name": matched_company_name,
        "location_match_source": location_match_source,
    }
