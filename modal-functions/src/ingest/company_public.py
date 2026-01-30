"""
Public Companies Ingest Endpoint

Simple endpoint to add known public companies.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class PublicCompanyRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_public_company(request: PublicCompanyRequest) -> dict:
    """
    Add a known public company to core.company_public.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Clean domain
        domain = request.domain.lower().strip()
        domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

        result = (
            supabase.schema("core")
            .from_("company_public")
            .upsert({
                "domain": domain,
                "company_name": request.company_name,
                "linkedin_url": request.linkedin_url,
            }, on_conflict="domain")
            .execute()
        )

        return {
            "success": True,
            "domain": domain,
            "company_name": request.company_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
