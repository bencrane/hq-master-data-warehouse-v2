"""
Send Case Study URLs to Clay Webhook

Reads unprocessed/unsent URLs from raw.staging_case_study_urls
and sends them to a Clay webhook at 10 records/second.
Marks each row as sent_to_clay after successful send.
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
def send_case_study_urls_to_clay(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    webhook_url = request.get("webhook_url")
    batch_id = request.get("batch_id")

    if not webhook_url:
        return {"success": False, "error": "webhook_url is required"}

    try:
        # Fetch unsent rows
        query = (
            supabase.schema("raw")
            .from_("staging_case_study_urls")
            .select("id, origin_company_name, origin_company_domain, customer_company_name, case_study_url")
            .eq("sent_to_clay", False)
        )
        if batch_id:
            query = query.eq("batch_id", batch_id)

        result = query.order("created_at").execute()
        rows = result.data or []

        if not rows:
            return {"success": True, "total_rows": 0, "sent": 0, "message": "No unsent rows found."}

        sent_count = 0
        for row in rows:
            payload = {
                "origin_company_name": row.get("origin_company_name"),
                "origin_company_domain": row.get("origin_company_domain"),
                "customer_company_name": row.get("customer_company_name"),
                "case_study_url": row.get("case_study_url"),
            }
            try:
                requests.post(webhook_url, json=payload, timeout=10)
            except Exception:
                pass

            # Mark as sent
            try:
                supabase.schema("raw").from_("staging_case_study_urls").update(
                    {"sent_to_clay": True}
                ).eq("id", row["id"]).execute()
            except Exception:
                pass

            sent_count += 1
            time.sleep(0.1)  # 10 records/second

        return {
            "success": True,
            "total_rows": len(rows),
            "sent": sent_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
