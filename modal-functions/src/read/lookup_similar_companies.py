"""
Lookup Similar Companies Preview Endpoint

Checks if similar companies have been generated for a given domain.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class SimilarCompaniesLookupRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_similar_companies(request: SimilarCompaniesLookupRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("core")
            .from_("company_similar_companies_preview")
            .select("input_domain", count="exact")
            .eq("input_domain", request.domain.lower().strip())
            .limit(1)
            .execute()
        )

        found = result.count > 0 if result.count is not None else len(result.data) > 0

        return {
            "success": True,
            "found": found,
            "domain": request.domain,
            "similar_count": result.count or 0,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
