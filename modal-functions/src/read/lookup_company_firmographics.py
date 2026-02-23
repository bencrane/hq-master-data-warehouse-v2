"""
Lookup Company Firmographics Endpoint

Returns description and industry for a company from extracted.company_firmographics.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CompanyFirmographicsRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_firmographics(request: CompanyFirmographicsRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    domain = request.domain.lower().strip()

    try:
        result = (
            supabase.schema("extracted")
            .from_("company_firmographics")
            .select("description, industry, matched_industry")
            .eq("company_domain", domain)
            .limit(1)
            .execute()
        )

        if not result.data:
            return {
                "success": True,
                "found": False,
                "domain": domain,
            }

        row = result.data[0]
        return {
            "success": True,
            "found": True,
            "domain": domain,
            "description": row.get("description"),
            "industry": row.get("matched_industry") or row.get("industry"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
