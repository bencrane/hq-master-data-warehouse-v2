"""
Lookup Company Canonical

Returns cleaned_name and linkedin_url for a given domain.
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_canonical(request: dict) -> dict:
    """
    Lookup canonical company data by domain.

    Input: {"domain": "datadoghq.com"}
    Output: {"domain": "...", "cleaned_name": "...", "linkedin_url": "..."}
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    domain = request.get("domain", "").lower().strip()

    if not domain:
        return {"success": False, "error": "Missing domain"}

    try:
        result = (
            supabase.schema("core")
            .from_("company_canonical")
            .select("domain, original_name, cleaned_name, linkedin_url")
            .eq("domain", domain)
            .limit(1)
            .execute()
        )

        if result.data:
            record = result.data[0]
            return {
                "success": True,
                "found": True,
                "domain": record.get("domain"),
                "original_name": record.get("original_name"),
                "cleaned_name": record.get("cleaned_name"),
                "linkedin_url": record.get("linkedin_url"),
            }
        else:
            return {
                "success": True,
                "found": False,
                "domain": domain,
                "original_name": None,
                "cleaned_name": None,
                "linkedin_url": None,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
