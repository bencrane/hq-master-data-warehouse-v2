"""
Lookup Company Description Endpoint

Returns description and tagline for a company from core.company_descriptions.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class CompanyDescriptionLookupRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_description(request: CompanyDescriptionLookupRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("core")
            .from_("company_descriptions")
            .select("domain, description, tagline, source")
            .eq("domain", request.domain.lower().strip())
            .limit(1)
            .execute()
        )

        if not result.data:
            return {
                "success": True,
                "found": False,
                "domain": request.domain,
            }

        row = result.data[0]
        return {
            "success": True,
            "found": True,
            "domain": row["domain"],
            "description": row.get("description"),
            "tagline": row.get("tagline"),
            "source": row.get("source"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
