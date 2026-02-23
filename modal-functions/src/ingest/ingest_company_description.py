"""
Ingest Company Description

Inserts a company description into core.company_descriptions.
Only inserts if the domain doesn't already exist (no overwrite).

Expects:
{
  "domain": "example.com",
  "description": "Company meta description text",
  "source": "site-meta-description"  // optional, defaults to "site-meta-description"
}

Returns:
{
  "success": true,
  "domain": "example.com",
  "inserted": true  // false if domain already existed
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=30,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_description(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").strip().lower()
        description = request.get("description", "").strip()
        source = request.get("source", "site-meta-description").strip()

        if not domain:
            return {"success": False, "error": "domain is required"}
        if not description:
            return {"success": False, "error": "description is required"}

        # Check if domain already exists
        existing = (
            supabase.schema("core")
            .from_("company_descriptions")
            .select("domain")
            .eq("domain", domain)
            .limit(1)
            .execute()
        )

        if existing.data:
            return {
                "success": True,
                "domain": domain,
                "inserted": False,
                "message": "Domain already exists, skipped"
            }

        # Insert new record
        supabase.schema("core").from_("company_descriptions").insert({
            "domain": domain,
            "description": description,
            "source": source,
        }).execute()

        return {
            "success": True,
            "domain": domain,
            "inserted": True
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
