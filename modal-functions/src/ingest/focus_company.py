"""
Ingest Focus Company

Receives a company domain (and optional name) from Clay
and upserts it into public.focus_companies.
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_focus_company(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    domain = (request.get("domain") or "").lower().strip().rstrip("/")
    if not domain:
        return {"success": False, "error": "domain is required"}

    company_name = request.get("company_name", "")

    try:
        supabase.from_("focus_companies").upsert(
            {"domain": domain, "company_name": company_name},
            on_conflict="domain",
        ).execute()

        return {"success": True, "domain": domain, "company_name": company_name}
    except Exception as e:
        return {"success": False, "error": str(e)}
