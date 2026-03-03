"""
Lookup Company by LinkedIn ID

Takes a LinkedIn company/org ID and returns company name, domain,
LinkedIn URL, and description.
"""

import os
import modal
from pydantic import BaseModel, Field
from typing import Optional

from config import app, image


class LookupCompanyByLinkedInIDRequest(BaseModel):
    linkedin_company_id: int = Field(description="LinkedIn numeric org ID")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_by_linkedin_id(request: LookupCompanyByLinkedInIDRequest) -> dict:
    """
    Lookup company by LinkedIn org ID.
    Returns name, domain, linkedin_url, and description.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Query extracted.company_discovery_location_parsed
        result = (
            supabase.schema("extracted")
            .from_("company_discovery_location_parsed")
            .select("domain, name, linkedin_url, linkedin_company_id")
            .eq("linkedin_company_id", request.linkedin_company_id)
            .limit(1)
            .execute()
        )

        if not result.data:
            return {
                "success": False,
                "error": "Company not found",
                "linkedin_company_id": request.linkedin_company_id,
            }

        company = result.data[0]
        domain = company.get("domain")

        # Try to get description from core.companies_full
        description = None
        if domain:
            desc_result = (
                supabase.schema("core")
                .from_("companies_full")
                .select("description")
                .eq("domain", domain)
                .limit(1)
                .execute()
            )
            if desc_result.data:
                description = desc_result.data[0].get("description")

        return {
            "success": True,
            "linkedin_company_id": request.linkedin_company_id,
            "name": company.get("name"),
            "domain": domain,
            "linkedin_url": company.get("linkedin_url"),
            "description": description,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "linkedin_company_id": request.linkedin_company_id,
        }
