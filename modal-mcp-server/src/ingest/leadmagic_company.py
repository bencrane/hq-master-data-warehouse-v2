"""
LeadMagic Company Enrichment Ingestion Endpoint

Ingests company enrichment data from LeadMagic.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any

from config import app, image


class LeadMagicCompanyRequest(BaseModel):
    domain: Optional[str] = None
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    raw_payload: Optional[dict] = None
    workflow_slug: Optional[str] = "leadmagic-company-enrichment"


def safe_get(d: dict, *keys, default=None):
    """Safely get nested dict values."""
    for key in keys:
        if d is None or not isinstance(d, dict):
            return default
        d = d.get(key)
    return d if d is not None else default


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_leadmagic_company(request: LeadMagicCompanyRequest) -> dict:
    """
    Ingest LeadMagic company enrichment data.
    Stores raw payload, then extracts key fields.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("leadmagic_company_enrichment")
            .insert({
                "domain": request.domain,
                "company_name": request.company_name,
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract fields from raw_payload
        payload = request.raw_payload or {}
        
        # Get headquarter location
        hq = payload.get("headquarter") or {}
        
        # Get employee range
        emp_range = payload.get("employeeCountRange") or {}
        
        # Get founded year
        founded = payload.get("foundedOn") or {}

        extracted_data = {
            "raw_payload_id": raw_id,
            "domain": request.domain,
            "company_name": request.company_name or payload.get("companyName"),
            "linkedin_url": request.linkedin_url or payload.get("url"),
            "linkedin_company_id": payload.get("companyId"),
            "universal_name": payload.get("universalName"),
            "description": payload.get("description"),
            "tagline": payload.get("tagline"),
            "industry": payload.get("industry"),
            "website_url": payload.get("websiteUrl"),
            "logo_url": payload.get("logoResolutionResult"),
            "founded_year": founded.get("year"),
            "employee_count": payload.get("employeeCount"),
            "employee_range_start": emp_range.get("start"),
            "employee_range_end": emp_range.get("end"),
            "follower_count": payload.get("followerCount"),
            "city": hq.get("city"),
            "state": hq.get("geographicArea"),
            "country": hq.get("country"),
            "postal_code": hq.get("postalCode"),
            "specialties": payload.get("specialities") if payload.get("specialities") else None,
        }

        extracted_insert = (
            supabase.schema("extracted")
            .from_("leadmagic_company_enrichment")
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
