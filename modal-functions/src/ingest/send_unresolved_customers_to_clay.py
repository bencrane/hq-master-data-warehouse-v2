"""
Send Unresolved Customer Names to Clay Webhook

Reads company customers with no domain and no case study URL
from core.company_customers and sends them to a Clay webhook at 10 records/second.
"""

import os
import time
import modal
import requests
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def send_unresolved_customers_to_clay(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    webhook_url = request.get("webhook_url")
    limit = request.get("limit")

    if not webhook_url:
        return {"success": False, "error": "webhook_url is required"}

    try:
        query = (
            supabase.schema("core")
            .from_("company_customers")
            .select("id, customer_name, origin_company_domain, origin_company_name")
            .is_("customer_domain", "null")
            .is_("case_study_url", "null")
            .neq("customer_name", "none found")
            .neq("customer_name", "none found.")
            .order("created_at")
        )
        if limit:
            query = query.limit(limit)

        result = query.execute()
        rows = result.data or []

        if not rows:
            return {"success": True, "total_rows": 0, "sent": 0, "message": "No unresolved rows found."}

        sent_count = 0
        for row in rows:
            payload = {
                "id": row["id"],
                "customer_name": row.get("customer_name"),
                "origin_company_domain": row.get("origin_company_domain"),
                "origin_company_name": row.get("origin_company_name"),
            }
            try:
                requests.post(webhook_url, json=payload, timeout=10)
            except Exception:
                pass

            sent_count += 1
            time.sleep(0.1)

        return {
            "success": True,
            "total_rows": len(rows),
            "sent": sent_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
