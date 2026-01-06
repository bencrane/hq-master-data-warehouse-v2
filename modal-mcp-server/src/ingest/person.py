"""
Person Ingestion Endpoints

- ingest_person_payload: Enriched person data (clay-person-profile)
- ingest_person_discovery: Discovery person data (clay-find-people)
"""

import os
import modal

from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_person_payload(request: dict) -> dict:
    """
    Ingest enriched person payload (clay-person-profile workflow).
    Stores raw payload, then extracts to person_profile, person_experience, person_education.
    """
    from supabase import create_client
    from extraction.person import (
        extract_person_profile,
        extract_person_experience,
        extract_person_education,
    )

    linkedin_url = request.get("linkedin_url")
    workflow_slug = request.get("workflow_slug")
    raw_payload = request.get("raw_payload")

    if not linkedin_url or not workflow_slug or not raw_payload:
        return {"success": False, "error": "Missing required fields: linkedin_url, workflow_slug, raw_payload"}

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{workflow_slug}' not found"}

        raw_insert = (
            supabase.schema("raw")
            .from_("person_payloads")
            .insert({
                "linkedin_url": linkedin_url,
                "workflow_slug": workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        person_profile_id = extract_person_profile(
            supabase, raw_id, linkedin_url, raw_payload
        )

        experience_count = extract_person_experience(
            supabase, raw_id, linkedin_url, raw_payload
        )

        education_count = extract_person_education(
            supabase, raw_id, linkedin_url, raw_payload
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
def ingest_person_discovery(request: dict) -> dict:
    """
    Ingest person discovery payload (clay-find-people workflow).
    Stores raw payload, then extracts to person_discovery table.
    """
    from supabase import create_client
    from extraction.person import extract_person_discovery

    linkedin_url = request.get("linkedin_url")
    workflow_slug = request.get("workflow_slug")
    raw_payload = request.get("raw_payload")

    if not linkedin_url or not workflow_slug or not raw_payload:
        return {"success": False, "error": "Missing required fields: linkedin_url, workflow_slug, raw_payload"}

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{workflow_slug}' not found"}

        raw_insert = (
            supabase.schema("raw")
            .from_("person_discovery")
            .insert({
                "linkedin_url": linkedin_url,
                "workflow_slug": workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_id = extract_person_discovery(
            supabase, raw_id, linkedin_url, raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
