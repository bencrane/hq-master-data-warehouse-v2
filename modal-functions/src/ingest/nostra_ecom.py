"""
Nostra Ecom Companies Ingestion Endpoint

Ingests company data from old Nostra ecom companies list.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class NostraEcomCompanyRequest(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    workflow_slug: Optional[str] = "nostra-ecom-companies"


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
def ingest_nostra_ecom_company(request: NostraEcomCompanyRequest) -> dict:
    """
    Ingest Nostra ecom company data.
    Stores raw payload, then extracts to nostra_ecom_companies.
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
            .from_("nostra_ecom_companies")
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
            "name": normalize_null_string(request.name),
            "domain": normalize_null_string(request.domain),
            "linkedin_url": normalize_null_string(request.linkedin_url),
            "description": normalize_null_string(request.description),
            "city": normalize_null_string(request.city),
            "state": normalize_null_string(request.state),
            "country": normalize_null_string(request.country),
        }

        extracted_insert = (
            supabase.schema("extracted")
            .from_("nostra_ecom_companies")
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
