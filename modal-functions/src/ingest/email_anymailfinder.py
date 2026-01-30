"""
AnyMailFinder Email Ingestion

Ingest endpoint for AnyMailFinder email lookup results.
Stores raw payload, extracts to normalized table, and builds reference tables.

Provider: AnyMailFinder
Entity Type: Person (email)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.email_anymailfinder import extract_email_anymailfinder


class AnyMailFinderRequest(BaseModel):
    # Canonical fields (from Clay context - source of truth)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None

    # The AnyMailFinder response payload
    anymailfinder_raw_payload: dict

    # Metadata
    workflow_slug: str = "anymailfinder-email"
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_email_anymailfinder(request: AnyMailFinderRequest) -> dict:
    """
    Ingest AnyMailFinder email lookup results.

    Stores raw payload, extracts to extracted.email_anymailfinder,
    and populates reference tables:
    - reference.email_structure_by_domain (email patterns)
    - reference.email_to_person (email -> linkedin mapping)
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
            "anymailfinder_raw_payload": request.anymailfinder_raw_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("email_anymailfinder")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract to normalized table and update reference tables
        extraction_result = extract_email_anymailfinder(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            person_linkedin_url=request.person_linkedin_url,
            first_name=request.first_name,
            last_name=request.last_name,
            full_name=request.full_name,
            domain=request.domain,
            company_name=request.company_name,
            company_linkedin_url=request.company_linkedin_url,
            anymailfinder_payload=request.anymailfinder_raw_payload,
        )

        # Get email from payload for response
        email = request.anymailfinder_raw_payload.get("results", {}).get("email")

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "email": email,
            "person_mapping_updated": extraction_result.get("person_mapping_updated"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
