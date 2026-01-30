"""
Nostra Ecom People Ingestion Endpoint

Ingests people data from old Nostra ecom companies list.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class NostraEcomPersonRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    person_linkedin_url: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    workflow_slug: Optional[str] = "nostra-ecom-people"


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_nostra_ecom_person(request: NostraEcomPersonRequest) -> dict:
    """
    Ingest Nostra ecom person data.
    Stores raw payload, then extracts to nostra_ecom_people.
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
            .from_("nostra_ecom_people")
            .insert({
                "domain": request.domain,
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract to extracted table
        extracted_data = {
            "raw_payload_id": raw_id,
            "first_name": normalize_null_string(request.first_name),
            "last_name": normalize_null_string(request.last_name),
            "email": normalize_null_string(request.email),
            "company_name": normalize_null_string(request.company_name),
            "domain": normalize_null_string(request.domain),
            "person_linkedin_url": normalize_null_string(request.person_linkedin_url),
            "company_linkedin_url": normalize_null_string(request.company_linkedin_url),
        }

        extracted_insert = (
            supabase.schema("extracted")
            .from_("nostra_ecom_people")
            .insert(extracted_data)
            .execute()
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_insert.data[0]["id"] if extracted_insert.data else None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
