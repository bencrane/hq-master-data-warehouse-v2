"""
Clay Native Person Ingestion Endpoint

Ingests person profile data from Clay native enrichment.
Does NOT require workflow registry lookup - uses hardcoded workflow_slug.

Populates:
- raw.person_payloads (raw JSON)
- extracted.person_profile (flattened profile)
- extracted.person_experience (work history)
- extracted.person_education (education)
- core.people (person record)
- core.companies (companies from experience)
- core.person_locations (location)
- core.person_tenure (job start date)
- core.person_past_employer (past employers)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List

from config import app, image
from extraction.person import (
    extract_person_profile,
    extract_person_experience,
    extract_person_education,
)
from extraction.person_core import (
    upsert_core_person,
    upsert_core_person_location,
    upsert_core_person_tenure,
    insert_core_person_past_employers,
    extract_companies_from_experience,
)


# Hardcoded workflow metadata
WORKFLOW_SLUG = "clay-native-person-enrichment"
PROVIDER = "clay"
PLATFORM = "modal"
PAYLOAD_TYPE = "enrichment"


class ClayNativePersonRequest(BaseModel):
    """Single person payload - the raw Clay enrichment response."""
    payload: dict


class ClayNativePersonBatchRequest(BaseModel):
    """Batch of person payloads."""
    payloads: List[dict]


def process_single_person(supabase, payload: dict) -> dict:
    """
    Process a single person payload.
    Returns dict with success status and IDs.
    """
    # Extract linkedin_url from payload
    linkedin_url = payload.get("url")
    if not linkedin_url:
        return {"success": False, "error": "Missing 'url' field in payload"}

    # Store raw payload
    raw_insert = (
        supabase.schema("raw")
        .from_("person_payloads")
        .insert({
            "linkedin_url": linkedin_url,
            "workflow_slug": WORKFLOW_SLUG,
            "provider": PROVIDER,
            "platform": PLATFORM,
            "payload_type": PAYLOAD_TYPE,
            "raw_payload": payload,
        })
        .execute()
    )
    raw_id = raw_insert.data[0]["id"]

    # Extract profile (upserts on linkedin_url)
    person_profile_id = extract_person_profile(
        supabase, raw_id, linkedin_url, payload
    )

    # Extract experience (delete + insert)
    experience_count = extract_person_experience(
        supabase, raw_id, linkedin_url, payload
    )

    # Extract education (delete + insert)
    education_count = extract_person_education(
        supabase, raw_id, linkedin_url, payload
    )

    # Populate core tables
    # 1. core.people - check/insert person
    core_person_id = upsert_core_person(
        supabase, linkedin_url, payload
    )

    # 2. core.companies - extract companies from experience
    companies_count = extract_companies_from_experience(
        supabase, payload
    )

    # 3. core.person_locations - upsert location
    core_location_id = upsert_core_person_location(
        supabase, linkedin_url, payload
    )

    # 4. core.person_tenure - upsert tenure (job start date)
    core_tenure_id = upsert_core_person_tenure(
        supabase, linkedin_url, payload
    )

    # 5. core.person_past_employer - insert past employers
    past_employers_count = insert_core_person_past_employers(
        supabase, linkedin_url, payload
    )

    return {
        "success": True,
        "linkedin_url": linkedin_url,
        "raw_id": raw_id,
        "person_profile_id": person_profile_id,
        "experience_count": experience_count,
        "education_count": education_count,
        "core_person_id": core_person_id,
        "companies_count": companies_count,
        "core_location_id": core_location_id,
        "core_tenure_id": core_tenure_id,
        "past_employers_count": past_employers_count,
    }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_native_person(request: ClayNativePersonRequest) -> dict:
    """
    Ingest a single Clay native person profile.

    Expects payload with 'url' field containing LinkedIn URL.
    Stores raw payload, extracts to profile/experience/education,
    and populates core tables.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        return process_single_person(supabase, request.payload)
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_native_person_batch(request: ClayNativePersonBatchRequest) -> dict:
    """
    Ingest a batch of Clay native person profiles.

    Each payload must have 'url' field containing LinkedIn URL.
    Processes all payloads and returns results for each.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    results = []
    success_count = 0
    error_count = 0

    for payload in request.payloads:
        try:
            result = process_single_person(supabase, payload)
            results.append(result)
            if result.get("success"):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            import traceback
            results.append({
                "success": False,
                "linkedin_url": payload.get("url"),
                "error": str(e),
                "traceback": traceback.format_exc(),
            })
            error_count += 1

    return {
        "success": error_count == 0,
        "total": len(request.payloads),
        "success_count": success_count,
        "error_count": error_count,
        "results": results,
    }
