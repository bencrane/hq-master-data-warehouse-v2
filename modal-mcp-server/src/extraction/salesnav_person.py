"""
SalesNav Person Extraction Functions

Extract and flatten SalesNav person data from raw payloads.
"""

from typing import Optional


def extract_salesnav_person(
    supabase,
    raw_payload_id: str,
    first_name: Optional[str],
    last_name: Optional[str],
    cleaned_first_name: Optional[str],
    cleaned_last_name: Optional[str],
    cleaned_full_name: Optional[str],
    email: Optional[str],
    phone_number: Optional[str],
    profile_headline: Optional[str],
    profile_summary: Optional[str],
    job_title: Optional[str],
    cleaned_job_title: Optional[str],
    job_description: Optional[str],
    job_started_on: Optional[str],
    person_linkedin_sales_nav_url: Optional[str],
    linkedin_user_profile_urn: Optional[str],
    location_raw: Optional[str],
    city: Optional[str],
    state: Optional[str],
    country: Optional[str],
    has_city: bool,
    has_state: bool,
    has_country: bool,
    company_name: Optional[str],
    domain: Optional[str],
    company_linkedin_url: Optional[str],
    source_id: Optional[str],
    upload_id: Optional[str],
    notes: Optional[str],
    matching_filters: Optional[bool],
    source_created_at: Optional[str],
    clay_batch_number: Optional[str],
    sent_to_clay_at: Optional[str],
    export_title: Optional[str],
    export_timestamp: Optional[str],
) -> dict:
    """
    Extract SalesNav person data to extracted.salesnav_scrapes_person.
    Returns the inserted record.
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "first_name": first_name,
        "last_name": last_name,
        "cleaned_first_name": cleaned_first_name,
        "cleaned_last_name": cleaned_last_name,
        "cleaned_full_name": cleaned_full_name,
        "email": email,
        "phone_number": phone_number,
        "profile_headline": profile_headline,
        "profile_summary": profile_summary,
        "job_title": job_title,
        "cleaned_job_title": cleaned_job_title,
        "job_description": job_description,
        "job_started_on": job_started_on,
        "person_linkedin_sales_nav_url": person_linkedin_sales_nav_url,
        "linkedin_user_profile_urn": linkedin_user_profile_urn,
        "location_raw": location_raw,
        "city": city,
        "state": state,
        "country": country,
        "has_city": has_city,
        "has_state": has_state,
        "has_country": has_country,
        "company_name": company_name,
        "domain": domain,
        "company_linkedin_url": company_linkedin_url,
        "source_id": source_id,
        "upload_id": upload_id,
        "notes": notes,
        "matching_filters": matching_filters,
        "source_created_at": source_created_at,
        "clay_batch_number": clay_batch_number,
        "sent_to_clay_at": sent_to_clay_at,
        "export_title": export_title,
        "export_timestamp": export_timestamp,
    }

    result = (
        supabase.schema("extracted")
        .from_("salesnav_scrapes_person")
        .insert(extracted_data)
        .execute()
    )

    return result.data[0] if result.data else None
