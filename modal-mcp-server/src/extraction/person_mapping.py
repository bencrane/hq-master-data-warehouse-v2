"""
Person Mapping Functions

Maps extracted person data against lookup tables:
- Location → reference.location_parsed
- Job Title → reference.job_title_parsed
"""

from typing import Optional
from supabase import Client


def map_person_discovery(
    supabase: Client,
    extracted_id: str,
    linkedin_url: str,
    location: Optional[str],
    job_title: Optional[str],
) -> dict:
    """
    Map extracted person data against lookup tables and store in mapped.person_discovery.

    Args:
        supabase: Supabase client
        extracted_id: ID of the extracted.person_discovery record
        linkedin_url: Person's LinkedIn URL
        location: Raw location string to match
        job_title: Raw job title to match

    Returns:
        dict with matched values and status
    """
    # Initialize results
    matched_city = None
    matched_state = None
    matched_country = None
    location_match_source = None
    matched_cleaned_job_title = None
    matched_seniority = None
    matched_job_function = None
    job_title_match_source = None

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

    # 2. Match job title against reference.job_title_parsed
    if job_title:
        job_title_result = (
            supabase.schema("reference")
            .from_("job_title_parsed")
            .select("cleaned_job_title, seniority, job_function, source")
            .eq("raw_job_title", job_title)
            .limit(1)
            .execute()
        )
        if job_title_result.data:
            match = job_title_result.data[0]
            matched_cleaned_job_title = match.get("cleaned_job_title")
            matched_seniority = match.get("seniority")
            matched_job_function = match.get("job_function")
            job_title_match_source = match.get("source")

    # 3. Upsert to mapped.person_discovery
    mapped_data = {
        "extracted_id": extracted_id,
        "linkedin_url": linkedin_url,
        "original_location": location,
        "original_job_title": job_title,
        "matched_city": matched_city,
        "matched_state": matched_state,
        "matched_country": matched_country,
        "location_match_source": location_match_source,
        "matched_cleaned_job_title": matched_cleaned_job_title,
        "matched_seniority": matched_seniority,
        "matched_job_function": matched_job_function,
        "job_title_match_source": job_title_match_source,
    }

    result = (
        supabase.schema("mapped")
        .from_("person_discovery")
        .upsert(mapped_data, on_conflict="linkedin_url")
        .execute()
    )

    return {
        "mapped_id": result.data[0]["id"] if result.data else None,
        "matched_city": matched_city,
        "matched_state": matched_state,
        "matched_country": matched_country,
        "matched_cleaned_job_title": matched_cleaned_job_title,
        "matched_seniority": matched_seniority,
        "matched_job_function": matched_job_function,
    }
