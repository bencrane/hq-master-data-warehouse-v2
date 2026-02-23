"""
Validate Export Title Endpoint

Simple endpoint to check if an export_title matches a scrape settings record.
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def validate_export_title(payload: dict) -> dict:
    """
    Check if export_title matches a salesnav_scrape_settings record.

    Input: {"export_title": "..."}
    Output: {"matched": true/false, "scrape_settings_id": "...", "koolkit_title": "..."}
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    export_title = payload.get("export_title", "").strip()
    if not export_title:
        return {"matched": False, "error": "export_title is required"}

    # Try exact match first
    result = (
        supabase.schema("public")
        .from_("salesnav_scrape_settings")
        .select("id, koolkit_title, include_exclude_filters")
        .eq("koolkit_title", export_title)
        .limit(1)
        .execute()
    )

    if result.data:
        settings = result.data[0]
        filters = settings.get("include_exclude_filters") or {}
        past_company = filters.get("pastCompany", {}).get("included", [])
        current_company = filters.get("currentCompany", {}).get("included", [])

        return {
            "matched": True,
            "match_type": "exact",
            "scrape_settings_id": settings["id"],
            "koolkit_title": settings["koolkit_title"][:100] + "..." if len(settings["koolkit_title"]) > 100 else settings["koolkit_title"],
            "past_company_filter": past_company,
            "current_company_filter": current_company,
        }

    # If no exact match, try prefix match (strip URL from export_title)
    if " - https://" in export_title:
        export_prefix = export_title.split(" - https://")[0] + " -"

        result = (
            supabase.schema("public")
            .from_("salesnav_scrape_settings")
            .select("id, koolkit_title, include_exclude_filters")
            .like("koolkit_title", f"{export_prefix}%")
            .limit(1)
            .execute()
        )

        if result.data:
            settings = result.data[0]
            filters = settings.get("include_exclude_filters") or {}
            past_company = filters.get("pastCompany", {}).get("included", [])
            current_company = filters.get("currentCompany", {}).get("included", [])

            return {
                "matched": True,
                "match_type": "prefix",
                "scrape_settings_id": settings["id"],
                "koolkit_title": settings["koolkit_title"][:100] + "..." if len(settings["koolkit_title"]) > 100 else settings["koolkit_title"],
                "past_company_filter": past_company,
                "current_company_filter": current_company,
                "prefix_used": export_prefix[:80] + "...",
            }

    return {
        "matched": False,
        "export_title_preview": export_title[:100] + "..." if len(export_title) > 100 else export_title,
    }
