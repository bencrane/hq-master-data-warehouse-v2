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


def extract_find_companies(supabase, raw_payload_id: str, company_domain: str, payload: dict, clay_table_url: str = None) -> tuple:
    """
    Extract company discovery data from raw payload to extracted.company_discovery.
    Upserts on domain, but only if linkedin_url matches (or no existing record).
    
    Returns:
        tuple: (extracted_id, status) where status is 'inserted', 'updated', or 'skipped_conflict'
    """
    incoming_linkedin_url = payload.get("linkedin_url")
    
    # Check if record already exists for this domain
    existing = (
        supabase.schema("extracted")
        .from_("company_discovery")
        .select("id, linkedin_url")
        .eq("domain", company_domain)
        .execute()
    )
    
    if existing.data:
        existing_record = existing.data[0]
        existing_linkedin_url = existing_record.get("linkedin_url")
        
        # If existing record has a linkedin_url and it doesn't match incoming, skip
        if existing_linkedin_url is not None and incoming_linkedin_url is not None:
            if existing_linkedin_url != incoming_linkedin_url:
                return (None, "skipped_conflict", existing_linkedin_url, incoming_linkedin_url)
    
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
        "clay_table_url": clay_table_url,
    }

    # Upsert on domain
    result = (
        supabase.schema("extracted")
        .from_("company_discovery")
        .upsert(extracted_data, on_conflict="domain")
        .execute()
    )

    status = "updated" if existing.data else "inserted"
    return (result.data[0]["id"] if result.data else None, status)


def extract_company_customers_claygent(
    supabase, 
    raw_payload_id: str, 
    origin_company_domain: str, 
    origin_company_name: str,
    payload: dict
) -> int:
    """
    Extract customer companies from Claygent payload to extracted.company_customer_claygent.
    Explodes the customers array into individual rows.
    Upserts on (origin_company_domain, customer_company_name).
    
    Returns count of customers extracted.
    """
    customers = payload.get("customers", [])
    
    if not customers:
        return 0
    
    extracted_count = 0
    
    for customer in customers:
        customer_name = customer.get("companyName")
        if not customer_name:
            continue
            
        extracted_data = {
            "raw_payload_id": raw_payload_id,
            "origin_company_domain": origin_company_domain,
            "origin_company_name": origin_company_name,
            "company_customer_name": customer_name,
            "case_study_url": customer.get("url"),
            "has_case_study": customer.get("hasCaseStudy", False),
        }
        
        # Upsert on (origin_company_domain, company_customer_name)
        try:
            supabase.schema("extracted").from_("company_customer_claygent").upsert(
                extracted_data, 
                on_conflict="origin_company_domain,company_customer_name"
            ).execute()
            extracted_count += 1
        except Exception as e:
            # Log but continue with other customers
            print(f"Failed to upsert customer {customer_name}: {e}")
    
    return extracted_count


def extract_find_companies_location_parsed(
    supabase,
    raw_payload_id: str,
    company_domain: str,
    payload: dict,
    parsed_location: dict,
    clay_table_url: str = None
) -> Optional[str]:
    """
    Extract company discovery data with pre-parsed location fields.
    Upserts on domain to extracted.company_discovery_location_parsed.
    
    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_domain: Company domain
        payload: Raw company payload dict
        parsed_location: Pre-parsed location dict with city, state, hasCity, hasState
        clay_table_url: Optional Clay table URL
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
        # Location fields
        "country": payload.get("country"),
        "location": payload.get("location"),
        "city": parsed_location.get("city") if parsed_location else None,
        "state": parsed_location.get("state") if parsed_location else None,
        "has_city": parsed_location.get("hasCity", False) if parsed_location else False,
        "has_state": parsed_location.get("hasState", False) if parsed_location else False,
        # Industry/business info
        "industry": payload.get("industry"),
        "industries": payload.get("industries"),
        "description": payload.get("description"),
        "annual_revenue": payload.get("annual_revenue"),
        "total_funding_amount_range_usd": payload.get("total_funding_amount_range_usd"),
        "resolved_domain": payload.get("resolved_domain"),
        "derived_datapoints": payload.get("derived_datapoints"),
        "clay_table_url": clay_table_url,
    }

    # Upsert on domain
    result = (
        supabase.schema("extracted")
        .from_("company_discovery_location_parsed")
        .upsert(extracted_data, on_conflict="domain")
        .execute()
    )

    return result.data[0]["id"] if result.data else None
