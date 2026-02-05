"""
Case Study Details Lookup Endpoint

Check if case study extraction has been done for a given domain.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CaseStudyDetailsLookupRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_case_study_details(request: CaseStudyDetailsLookupRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("extracted")
            .from_("case_study_details")
            .select("id", count="exact")
            .eq("origin_company_domain", request.domain)
            .limit(1)
            .execute()
        )

        count = result.count or 0

        return {
            "exists": count > 0,
            "domain": request.domain,
            "count": count,
        }

    except Exception as e:
        return {"exists": False, "domain": request.domain, "error": str(e)}
