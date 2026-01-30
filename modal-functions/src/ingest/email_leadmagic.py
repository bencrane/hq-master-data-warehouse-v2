"""
LeadMagic Email Ingestion

Ingest endpoint for LeadMagic email lookup results.
Stores raw payload, extracts to normalized table, and updates reference.email_to_person.

Provider: LeadMagic
Entity Type: Person (email)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.email_leadmagic import extract_email_leadmagic


class LeadMagicRequest(BaseModel):
    # Canonical fields (from Clay context - source of truth)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None

    # The LeadMagic response payload
    leadmagic_raw_payload: dict

    # Metadata
    workflow_slug: str = "leadmagic-email"
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_email_leadmagic(request: LeadMagicRequest) -> dict:
    """
    Ingest LeadMagic email lookup results.

    Stores raw payload, extracts to extracted.email_leadmagic,
    and updates reference.email_to_person.
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
            return {
                "success": False,
                "error": f"Workflow '{request.workflow_slug}' not found in registry"
            }

        # Store raw payload
        raw_record = {
            "person_linkedin_url": request.person_linkedin_url,
            "first_name": request.first_name,
            "last_name": request.last_name,
            "full_name": request.full_name,
            "domain": request.domain,
            "company_name": request.company_name,
            "company_linkedin_url": request.company_linkedin_url,
            "workflow_slug": request.workflow_slug,
            "clay_table_url": request.clay_table_url,
            "leadmagic_raw_payload": request.leadmagic_raw_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("email_leadmagic")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract to normalized table and update reference table
        extraction_result = extract_email_leadmagic(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            person_linkedin_url=request.person_linkedin_url,
            first_name=request.first_name,
            last_name=request.last_name,
            full_name=request.full_name,
            domain=request.domain,
            company_name=request.company_name,
            company_linkedin_url=request.company_linkedin_url,
            leadmagic_payload=request.leadmagic_raw_payload,
        )

        # Get email from payload for response
        email = request.leadmagic_raw_payload.get("email")

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "email": email,
            "person_mapping_updated": extraction_result.get("person_mapping_updated"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
