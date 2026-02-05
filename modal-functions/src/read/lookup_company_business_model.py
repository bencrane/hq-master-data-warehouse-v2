"""
Lookup Company Business Model Endpoint

Returns B2B/B2C classification for a company from core.company_business_model.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class CompanyBusinessModelLookupRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_business_model(request: CompanyBusinessModelLookupRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("core")
            .from_("company_business_model")
            .select("domain, is_b2b, is_b2c")
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
            "is_b2b": row.get("is_b2b"),
            "is_b2c": row.get("is_b2c"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
