"""
Case Study Details Lookup Endpoint

Check if a case study URL has already been extracted.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CaseStudyDetailsLookupRequest(BaseModel):
    case_study_url: str


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
            .eq("case_study_url", request.case_study_url)
            .limit(1)
            .execute()
        )

        count = result.count or 0

        return {
            "exists": count > 0,
            "case_study_url": request.case_study_url,
        }

    except Exception as e:
        return {"exists": False, "case_study_url": request.case_study_url, "error": str(e)}
