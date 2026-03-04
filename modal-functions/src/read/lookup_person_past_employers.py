"""
Lookup Person Past Employers

Takes a LinkedIn URL and returns past employers from core.person_past_employer.
"""

import os
import modal
from pydantic import BaseModel, Field
from typing import Optional

from config import app, image


class LookupPersonPastEmployersRequest(BaseModel):
    linkedin_url: str = Field(min_length=1, description="Person's LinkedIn URL")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST")
def lookup_person_past_employers(request: LookupPersonPastEmployersRequest) -> dict:
    """
    Lookup past employers for a person by LinkedIn URL.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Normalize LinkedIn URL
        linkedin_url = request.linkedin_url.strip()

        # Query past employers
        result = (
            supabase.schema("core")
            .from_("person_past_employer")
            .select("past_company_name, past_company_domain, source, created_at")
            .eq("linkedin_url", linkedin_url)
            .execute()
        )

        if not result.data:
            return {
                "success": True,
                "found": False,
                "linkedin_url": linkedin_url,
                "past_employer_count": 0,
                "past_employers": [],
            }

        return {
            "success": True,
            "found": True,
            "linkedin_url": linkedin_url,
            "past_employer_count": len(result.data),
            "past_employers": result.data,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "linkedin_url": request.linkedin_url,
        }
