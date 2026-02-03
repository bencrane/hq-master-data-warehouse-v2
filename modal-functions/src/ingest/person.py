"""
Person Ingestion Endpoints

- ingest_clay_person_profile: Enriched person data (clay-person-profile)
- ingest_clay_find_people: Discovery person data (clay-find-people)
- ingest_clay_find_ppl_lctn_prsd: Discovery person data with pre-parsed location
- ingest_ppl_title_enrich: Person data with title enrichment (seniority, job function)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.person import (
    extract_person_profile,
    extract_person_experience,
    extract_person_education,
    extract_find_people,
    extract_find_people_location_parsed,
    extract_person_title_enrichment,
)
from extraction.person_mapping import map_person_discovery
from extraction.person_core import (
    upsert_core_person,
    upsert_core_person_location,
    upsert_core_person_tenure,
    insert_core_person_past_employers,
    extract_companies_from_experience,
)


class PersonIngestRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict


class PersonDiscoveryRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    clay_table_url: Optional[str] = None


class PersonDiscoveryLocationParsedRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_person_payload: dict
    raw_person_parsed_location_payload: Optional[dict] = None
    clay_table_url: Optional[str] = None


class PersonTitleEnrichmentRequest(BaseModel):
    linkedin_url: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    location_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = False
    has_state: Optional[bool] = False
    has_country: Optional[bool] = False
    company_domain: Optional[str] = None
    latest_title: Optional[str] = None
    cleaned_job_title: Optional[str] = None
    latest_company: Optional[str] = None
    latest_start_date: Optional[str] = None
    clay_company_table_id: Optional[str] = None
    clay_company_record_id: Optional[str] = None
    seniority_level: Optional[str] = None
    job_function: Optional[str] = None
    workflow_slug: str
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_person_profile(request: PersonIngestRequest) -> dict:
    """
    Ingest enriched person payload (clay-person-profile workflow).
    Stores raw payload, then extracts to person_profile, person_experience, person_education.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("person_payloads")
            .insert({
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract profile (upserts on linkedin_url)
        person_profile_id = extract_person_profile(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        # Extract experience (delete + insert)
        # Note: This triggers sync_person_experience_to_core() which populates core.person_work_history
        experience_count = extract_person_experience(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        # Extract education (delete + insert)
        education_count = extract_person_education(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        # Populate core tables
        # 1. core.people - check/insert person
        core_person_id = upsert_core_person(
            supabase, request.linkedin_url, request.raw_payload
        )

        # 2. core.companies - extract companies from experience
        companies_count = extract_companies_from_experience(
            supabase, request.raw_payload
        )

        # 3. core.person_locations - upsert location
        core_location_id = upsert_core_person_location(
            supabase, request.linkedin_url, request.raw_payload
        )

        # 4. core.person_tenure - upsert tenure (job start date)
        core_tenure_id = upsert_core_person_tenure(
            supabase, request.linkedin_url, request.raw_payload
        )

        # 5. core.person_past_employer - insert past employers
        past_employers_count = insert_core_person_past_employers(
            supabase, request.linkedin_url, request.raw_payload
        )

        return {
            "success": True,
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

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_find_people(request: PersonDiscoveryRequest) -> dict:
    """
    Ingest person discovery payload (clay-find-people workflow).
    Stores raw payload, then extracts to person_discovery table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("person_discovery")
            .insert({
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
                "clay_table_url": request.clay_table_url,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extracted_id = extract_find_people(
            supabase,
            raw_id,
            request.linkedin_url,
            request.raw_payload,
            request.clay_table_url,
            cleaned_first_name=request.cleaned_first_name,
            cleaned_last_name=request.cleaned_last_name,
            cleaned_full_name=request.cleaned_full_name,
        )

        # Map against lookup tables
        mapping_result = None
        if extracted_id:
            # Try both field names for job title
            job_title = request.raw_payload.get("latest_title") or request.raw_payload.get("latest_experience_title")
            mapping_result = map_person_discovery(
                supabase=supabase,
                extracted_id=extracted_id,
                linkedin_url=request.linkedin_url,
                location=request.raw_payload.get("location_name"),
                job_title=job_title,
            )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "mapped_id": mapping_result.get("mapped_id") if mapping_result else None,
            "matched_city": mapping_result.get("matched_city") if mapping_result else None,
            "matched_state": mapping_result.get("matched_state") if mapping_result else None,
            "matched_seniority": mapping_result.get("matched_seniority") if mapping_result else None,
            "matched_job_function": mapping_result.get("matched_job_function") if mapping_result else None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_find_ppl_lctn_prsd(request: PersonDiscoveryLocationParsedRequest) -> dict:
    """
    Ingest person discovery payload with pre-parsed location.
    Location parsing done in Clay via Gemini before sending to this endpoint.
    Stores raw payload + parsed location, then extracts to person_discovery_location_parsed table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("person_discovery_location_parsed")
            .insert({
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_person_payload": request.raw_person_payload,
                "raw_person_parsed_location_payload": request.raw_person_parsed_location_payload,
                "clay_table_url": request.clay_table_url,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract with parsed location
        extracted_id = extract_find_people_location_parsed(
            supabase,
            raw_id,
            request.linkedin_url,
            request.raw_person_payload,
            request.raw_person_parsed_location_payload,
            request.clay_table_url,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_ppl_title_enrich(request: PersonTitleEnrichmentRequest) -> dict:
    """
    Ingest person data with title enrichment (seniority_level, job_function, cleaned_job_title).
    Stores raw payload, then extracts to person_title_enrichment table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload from request
        raw_payload = request.model_dump()

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("person_title_enrichment")
            .insert({
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
                "clay_table_url": request.clay_table_url,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extracted_id = extract_person_title_enrichment(
            supabase,
            raw_id,
            raw_payload,
            request.clay_table_url,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
