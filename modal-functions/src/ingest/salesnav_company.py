"""
SalesNav Company Ingestion Endpoint

Ingests company data from SalesNav scrapes.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class SalesNavCompanyRequest(BaseModel):
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_urn: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    headcount: Optional[str] = None  # Comes as string from Clay
    industries: Optional[str] = None
    registered_address_raw: Optional[str] = None
    workflow_slug: Optional[str] = "salesnav-company"


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


def parse_headcount(value: Optional[str]) -> Optional[int]:
    """Parse headcount string to integer."""
    if value is None or value == "null" or value == "":
        return None
    try:
        # Remove commas and parse
        return int(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_company(request: SalesNavCompanyRequest) -> dict:
    """
    Ingest SalesNav company data.
    Stores raw payload, then extracts to salesnav_scrapes_companies.
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
            .from_("salesnav_scrapes_company_address_payloads")
            .insert({
                "company_name": normalize_null_string(request.company_name),
                "linkedin_url": normalize_null_string(request.linkedin_url),
                "linkedin_urn": normalize_null_string(request.linkedin_urn),
                "domain": normalize_null_string(request.domain),
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract to salesnav_scrapes_companies
        extracted_data = {
            "raw_payload_id": raw_id,
            "company_name": normalize_null_string(request.company_name),
            "linkedin_url": normalize_null_string(request.linkedin_url),
            "linkedin_urn": normalize_null_string(request.linkedin_urn),
            "domain": normalize_null_string(request.domain),
            "description": normalize_null_string(request.description),
            "headcount": parse_headcount(request.headcount),
            "industries": normalize_null_string(request.industries),
            "registered_address_raw": normalize_null_string(request.registered_address_raw),
            # Location fields left NULL - to be filled by lookup/parsing later
            "city": None,
            "state": None,
            "country": None,
            "has_city": False,
            "has_state": False,
            "has_country": False,
        }

        extracted_result = (
            supabase.schema("extracted")
            .from_("salesnav_scrapes_companies")
            .insert(extracted_data)
            .execute()
        )

        extracted_id = extracted_result.data[0]["id"] if extracted_result.data else None

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "domain": request.domain,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
