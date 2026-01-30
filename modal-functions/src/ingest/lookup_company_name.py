"""
Company Name Lookup Endpoint

Returns company name for a given domain.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CompanyNameLookupRequest(BaseModel):
    """Request model for company name lookup."""
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_name(request: CompanyNameLookupRequest) -> dict:
    """
    Lookup company name by domain.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("core")
            .from_("companies")
            .select("name, cleaned_name")
            .eq("domain", request.domain)
            .single()
            .execute()
        )

        if result.data:
            return {
                "success": True,
                "domain": request.domain,
                "company_name": result.data.get("cleaned_name") or result.data.get("name"),
            }
        else:
            return {
                "success": False,
                "domain": request.domain,
                "error": "Company not found",
            }

    except Exception as e:
        return {"success": False, "domain": request.domain, "error": str(e)}
