"""
SalesNav Person Ingestion Endpoint

Ingests person data from SalesNav scrapes.
Location is matched against reference.salesnav_location_lookup table.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.salesnav_person import extract_salesnav_person


class SalesNavPersonRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    profile_headline: Optional[str] = None
    profile_summary: Optional[str] = None
    job_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_started_on: Optional[str] = None
    person_linkedin_sales_nav_url: Optional[str] = None
    linkedin_user_profile_urn: Optional[str] = None
    location: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source_id: Optional[str] = None
    upload_id: Optional[str] = None
    notes: Optional[str] = None
    matching_filters: Optional[str] = None
    source_created_at: Optional[str] = None
    clay_batch_number: Optional[str] = None
    sent_to_clay_at: Optional[str] = None
    export_title: Optional[str] = None
    export_timestamp: Optional[str] = None
    workflow_slug: Optional[str] = "salesnav-person"


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


def parse_boolean_string(value: Optional[str]) -> Optional[bool]:
    """Parse boolean from string."""
    if value is None or value == "null" or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_person(request: SalesNavPersonRequest) -> dict:
    """
    Ingest SalesNav person data.
    Matches location against reference.salesnav_location_lookup.
    Stores raw payload, then extracts to salesnav_scrapes_person.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload
        raw_payload = request.model_dump()

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("salesnav_scrapes_person_payloads")
            .insert({
                "person_linkedin_sales_nav_url": request.person_linkedin_sales_nav_url,
                "linkedin_user_profile_urn": request.linkedin_user_profile_urn,
                "domain": request.domain,
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Lookup location from reference table
        location_raw = normalize_null_string(request.location)
        parsed_location = {
            "city": None,
            "state": None,
            "country": None,
            "has_city": False,
            "has_state": False,
            "has_country": False,
        }

        if location_raw:
            lookup_result = (
                supabase.schema("reference")
                .from_("salesnav_location_lookup")
                .select("*")
                .eq("location_raw", location_raw)
                .execute()
            )
            if lookup_result.data:
                loc = lookup_result.data[0]
                parsed_location = {
                    "city": loc.get("city"),
                    "state": loc.get("state"),
                    "country": loc.get("country"),
                    "has_city": loc.get("has_city", False),
                    "has_state": loc.get("has_state", False),
                    "has_country": loc.get("has_country", False),
                }

        # Extract
        extracted_result = extract_salesnav_person(
            supabase=supabase,
            raw_payload_id=raw_id,
            first_name=normalize_null_string(request.first_name),
            last_name=normalize_null_string(request.last_name),
            cleaned_first_name=normalize_null_string(request.cleaned_first_name),
            cleaned_last_name=normalize_null_string(request.cleaned_last_name),
            cleaned_full_name=normalize_null_string(request.cleaned_full_name),
            email=normalize_null_string(request.email),
            phone_number=normalize_null_string(request.phone_number),
            profile_headline=normalize_null_string(request.profile_headline),
            profile_summary=normalize_null_string(request.profile_summary),
            job_title=normalize_null_string(request.job_title),
            cleaned_job_title=normalize_null_string(request.cleaned_job_title),
            job_description=normalize_null_string(request.job_description),
            job_started_on=normalize_null_string(request.job_started_on),
            person_linkedin_sales_nav_url=normalize_null_string(request.person_linkedin_sales_nav_url),
            linkedin_user_profile_urn=normalize_null_string(request.linkedin_user_profile_urn),
            location_raw=location_raw,
            city=parsed_location["city"],
            state=parsed_location["state"],
            country=parsed_location["country"],
            has_city=parsed_location["has_city"],
            has_state=parsed_location["has_state"],
            has_country=parsed_location["has_country"],
            company_name=normalize_null_string(request.company_name),
            domain=normalize_null_string(request.domain),
            company_linkedin_url=normalize_null_string(request.company_linkedin_url),
            source_id=normalize_null_string(request.source_id),
            upload_id=normalize_null_string(request.upload_id),
            notes=normalize_null_string(request.notes),
            matching_filters=parse_boolean_string(request.matching_filters),
            source_created_at=normalize_null_string(request.source_created_at),
            clay_batch_number=normalize_null_string(request.clay_batch_number),
            sent_to_clay_at=normalize_null_string(request.sent_to_clay_at),
            export_title=normalize_null_string(request.export_title),
            export_timestamp=normalize_null_string(request.export_timestamp),
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_result["id"] if extracted_result else None,
            "location_matched": parsed_location["city"] is not None or parsed_location["country"] is not None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
