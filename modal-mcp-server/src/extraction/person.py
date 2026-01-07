"""
Person Extraction Functions

Extract and flatten person data from raw payloads.
"""

from typing import Any, Optional
from datetime import datetime


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string to DATE format. Returns None if unparseable."""
    if not date_str:
        return None
    try:
        # Handle various formats
        if "T" in date_str:
            return date_str.split("T")[0]
        return date_str[:10] if len(date_str) >= 10 else date_str
    except:
        return None


def extract_person_profile(supabase, raw_payload_id: str, linkedin_url: str, payload: dict) -> Optional[str]:
    """
    Extract person profile from raw payload to extracted.person_profile.
    Flattens latest_experience into the profile.
    Upserts on linkedin_url, only updates if source_last_refresh is newer.
    """
    latest_exp = payload.get("latest_experience", {}) or {}

    # Parse source_last_refresh
    source_last_refresh = None
    if payload.get("last_refresh"):
        try:
            source_last_refresh = payload["last_refresh"]
        except:
            pass

    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "linkedin_url": linkedin_url,
        "linkedin_slug": payload.get("slug"),
        "linkedin_profile_id": payload.get("profile_id"),
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "full_name": payload.get("name"),
        "headline": payload.get("headline"),
        "summary": payload.get("summary"),
        "country": payload.get("country"),
        "location_name": payload.get("location_name"),
        "connections": payload.get("connections"),
        "num_followers": payload.get("num_followers"),
        "picture_url": payload.get("picture_url_orig") or payload.get("picture_url_copy"),
        "jobs_count": payload.get("jobs_count"),
        # Flattened from latest_experience
        "latest_title": latest_exp.get("title"),
        "latest_company": latest_exp.get("company"),
        "latest_company_domain": latest_exp.get("company_domain"),
        "latest_company_linkedin_url": latest_exp.get("url"),
        "latest_company_linkedin_org_id": latest_exp.get("org_id"),
        "latest_locality": latest_exp.get("locality"),
        "latest_start_date": parse_date(latest_exp.get("start_date")),
        "latest_is_current": latest_exp.get("is_current"),
        # Sparse arrays as JSONB
        "certifications": payload.get("certifications"),
        "languages": payload.get("languages"),
        "courses": payload.get("courses"),
        "patents": payload.get("patents"),
        "projects": payload.get("projects"),
        "publications": payload.get("publications"),
        "volunteering": payload.get("volunteering"),
        "awards": payload.get("awards"),
        # Metadata
        "source_last_refresh": source_last_refresh,
    }

    # Check if existing record has older source_last_refresh
    existing = (
        supabase.schema("extracted")
        .from_("person_profile")
        .select("id, source_last_refresh")
        .eq("linkedin_url", linkedin_url)
        .execute()
    )

    if existing.data:
        existing_refresh = existing.data[0].get("source_last_refresh")
        if existing_refresh and source_last_refresh:
            if str(existing_refresh) >= str(source_last_refresh):
                # Existing is newer or same, skip update
                return existing.data[0]["id"]

        # Update existing
        result = (
            supabase.schema("extracted")
            .from_("person_profile")
            .update(extracted_data)
            .eq("linkedin_url", linkedin_url)
            .execute()
        )
        return existing.data[0]["id"]
    else:
        # Insert new
        result = (
            supabase.schema("extracted")
            .from_("person_profile")
            .insert(extracted_data)
            .execute()
        )
        return result.data[0]["id"] if result.data else None


def extract_person_experience(supabase, raw_payload_id: str, linkedin_url: str, payload: dict) -> int:
    """
    Extract person experience from raw payload to extracted.person_experience.
    Deletes existing records for this linkedin_url, then inserts new ones.
    Returns count of records inserted.
    """
    experience_array = payload.get("experience", []) or []

    if not experience_array:
        return 0

    # Delete existing experience records for this person
    supabase.schema("extracted").from_("person_experience").delete().eq(
        "linkedin_url", linkedin_url
    ).execute()

    # Insert new records
    records = []
    for idx, exp in enumerate(experience_array):
        records.append({
            "raw_payload_id": raw_payload_id,
            "linkedin_url": linkedin_url,
            "experience_order": idx,
            "title": exp.get("title"),
            "company": exp.get("company"),
            "company_domain": exp.get("company_domain"),
            "company_linkedin_url": exp.get("url"),
            "company_linkedin_org_id": exp.get("org_id"),
            "locality": exp.get("locality"),
            "summary": exp.get("summary"),
            "start_date": parse_date(exp.get("start_date")),
            "end_date": parse_date(exp.get("end_date")),
            "is_current": exp.get("is_current", False),
        })

    if records:
        supabase.schema("extracted").from_("person_experience").insert(records).execute()

    return len(records)


def extract_person_education(supabase, raw_payload_id: str, linkedin_url: str, payload: dict) -> int:
    """
    Extract person education from raw payload to extracted.person_education.
    Deletes existing records for this linkedin_url, then inserts new ones.
    Returns count of records inserted.
    """
    education_array = payload.get("education", []) or []

    if not education_array:
        return 0

    # Delete existing education records for this person
    supabase.schema("extracted").from_("person_education").delete().eq(
        "linkedin_url", linkedin_url
    ).execute()

    # Insert new records
    records = []
    for idx, edu in enumerate(education_array):
        records.append({
            "raw_payload_id": raw_payload_id,
            "linkedin_url": linkedin_url,
            "education_order": idx,
            "school_name": edu.get("school_name"),
            "degree": edu.get("degree"),
            "field_of_study": edu.get("field_of_study"),
            "grade": edu.get("grade"),
            "activities": edu.get("activities"),
            "start_date": parse_date(edu.get("start_date")),
            "end_date": parse_date(edu.get("end_date")),
        })

    if records:
        supabase.schema("extracted").from_("person_education").insert(records).execute()

    return len(records)


def extract_find_people(supabase, raw_payload_id: str, linkedin_url: str, payload: dict) -> Optional[str]:
    """
    Extract person discovery data from raw payload to extracted.person_discovery.
    Upserts on linkedin_url.
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "linkedin_url": linkedin_url,
        "first_name": payload.get("first_name"),
        "last_name": payload.get("last_name"),
        "full_name": payload.get("name"),
        "location_name": payload.get("location_name"),
        "company_domain": payload.get("domain"),
        "latest_title": payload.get("latest_experience_title"),
        "latest_company": payload.get("latest_experience_company"),
        "latest_start_date": parse_date(payload.get("latest_experience_start_date")),
        "clay_company_table_id": payload.get("company_table_id"),
        "clay_company_record_id": payload.get("company_record_id"),
    }

    # Upsert on linkedin_url
    result = (
        supabase.schema("extracted")
        .from_("person_discovery")
        .upsert(extracted_data, on_conflict="linkedin_url")
        .execute()
    )

    return result.data[0]["id"] if result.data else None
