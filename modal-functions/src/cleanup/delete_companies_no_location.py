"""
Delete companies with no location data from core.companies
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def delete_companies_no_location(batch_size: int = 1000) -> dict:
    """
    Delete companies that have no location data.
    Deletes in batches to avoid timeouts.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    # Get domains to delete
    result = (
        supabase.schema("core")
        .from_("companies_missing_location")
        .select("domain")
        .is_("discovery_location", "null")
        .is_("salesnav_location", "null")
        .limit(batch_size)
        .execute()
    )

    if not result.data:
        return {"success": True, "message": "No more companies to delete", "deleted": 0}

    domains = [r["domain"] for r in result.data if r["domain"]]

    if not domains:
        return {"success": True, "message": "No valid domains found", "deleted": 0}

    # Delete companies (people already deleted)
    delete_result = (
        supabase.schema("core")
        .from_("companies")
        .delete()
        .in_("domain", domains)
        .execute()
    )

    # Also clean up from missing_location table
    (
        supabase.schema("core")
        .from_("companies_missing_location")
        .delete()
        .in_("domain", domains)
        .execute()
    )

    deleted_count = len(delete_result.data) if delete_result.data else len(domains)

    return {
        "success": True,
        "deleted": deleted_count,
        "message": f"Deleted {deleted_count} companies. Run again if more remain."
    }
