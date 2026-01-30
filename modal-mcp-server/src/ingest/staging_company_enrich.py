"""
Staging Company Enrich

Updates company_linkedin_url on staging.companies_to_enrich records.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class StagingCompanyEnrichRequest(BaseModel):
    domain: str
    company_linkedin_url: Optional[str] = None
    short_description: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def update_staging_company_linkedin(request: StagingCompanyEnrichRequest) -> dict:
    """
    Update company_linkedin_url for a staging company by domain.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        update_data = {}
        if request.company_linkedin_url is not None:
            update_data["company_linkedin_url"] = request.company_linkedin_url
        if request.short_description is not None:
            update_data["short_description"] = request.short_description

        result = (
            supabase.schema("staging")
            .from_("companies_to_enrich")
            .update(update_data)
            .eq("domain", request.domain)
            .execute()
        )

        updated_count = len(result.data) if result.data else 0

        return {
            "success": True,
            "domain": request.domain,
            "updated_count": updated_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
