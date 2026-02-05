"""
Send Client Leads to Clay Webhook

Reads leads for a given client_domain from client.leads
and sends each to a Clay webhook at ~10 records/second.
"""

import os
import time
import modal
import requests
from config import app, image


CLAY_WEBHOOK_URL = "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-8ed82c8d-3740-4206-8dd5-51e580a5cbe2"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def send_client_leads_to_clay(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    client_domain = (request.get("client_domain") or "").lower().strip()
    if not client_domain:
        return {"success": False, "error": "client_domain is required"}

    webhook_url = request.get("webhook_url", CLAY_WEBHOOK_URL)

    try:
        # Get leads for this client
        result = (
            supabase.schema("client")
            .from_("leads")
            .select("id, full_name, person_linkedin_url, company_domain, company_name, source")
            .eq("client_domain", client_domain)
            .order("company_name")
            .execute()
        )
        rows = result.data or []

        if not rows:
            return {"success": True, "client_domain": client_domain, "total_rows": 0, "sent": 0}

        sent_count = 0
        errors = 0
        for row in rows:
            full_name = row.get("full_name") or ""
            name_parts = full_name.strip().split(" ", 1)

            payload = {
                "client_domain": client_domain,
                "lead_id": row["id"],
                "first_name": name_parts[0] if name_parts else None,
                "last_name": name_parts[1] if len(name_parts) > 1 else None,
                "full_name": full_name,
                "person_linkedin_url": row.get("person_linkedin_url"),
                "company_domain": row.get("company_domain"),
                "company_name": row.get("company_name"),
            }
            try:
                resp = requests.post(webhook_url, json=payload, timeout=10)
                if resp.status_code < 400:
                    sent_count += 1
                else:
                    errors += 1
            except Exception:
                errors += 1

            time.sleep(0.1)

        return {
            "success": True,
            "client_domain": client_domain,
            "total_rows": len(rows),
            "sent": sent_count,
            "errors": errors,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
