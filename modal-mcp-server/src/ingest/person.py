"""
Person Ingestion Endpoints

- ingest_clay_person_profile: Enriched person data (clay-person-profile)
- ingest_clay_find_people: Discovery person data (clay-find-people)
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
)


class PersonIngestRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict


class PersonDiscoveryRequest(BaseModel):
    linkedin_url: str
    workflow_slug: str
    raw_payload: dict


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
        experience_count = extract_person_experience(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        # Extract education (delete + insert)
        education_count = extract_person_education(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "person_profile_id": person_profile_id,
            "experience_count": experience_count,
            "education_count": education_count,
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
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extracted_id = extract_find_people(
            supabase, raw_id, request.linkedin_url, request.raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
