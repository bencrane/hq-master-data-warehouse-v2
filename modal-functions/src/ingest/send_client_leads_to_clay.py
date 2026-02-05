"""
Send Client Leads to Clay Webhooks

Reads leads for a given client_domain from client.leads
and sends each to two Clay webhooks at ~10 records/second:
  1. People table  — all lead fields (one row per lead)
  2. Companies table — company_name, domain, company_linkedin_url (deduplicated)
"""

import os
import time
import modal
import requests
from config import app, image


CLAY_PEOPLE_WEBHOOK_URL = "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-c457c170-b2bf-4e66-83f5-83eda8f27092"
CLAY_COMPANIES_WEBHOOK_URL = "https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-965490f3-a855-4622-837e-be7224a13271"


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

    client_name = request.get("client_name", "")

    try:
        # Get leads for this client
        result = (
            supabase.schema("client")
            .from_("leads")
            .select("id, full_name, person_linkedin_url, company_domain, company_name, company_linkedin_url, source")
            .eq("client_domain", client_domain)
            .order("company_name")
            .execute()
        )
        rows = result.data or []

        if not rows:
            return {"success": True, "client_domain": client_domain, "total_rows": 0, "people_sent": 0, "companies_sent": 0}

        # Batch lookup company_linkedin_url from core.companies for any missing
        domains = list({r["company_domain"] for r in rows if r.get("company_domain")})
        company_linkedin_map = {}
        if domains:
            comp_result = (
                supabase.schema("core")
                .from_("companies")
                .select("domain, linkedin_url")
                .in_("domain", domains)
                .execute()
            )
            for c in (comp_result.data or []):
                if c.get("linkedin_url"):
                    company_linkedin_map[c["domain"]] = c["linkedin_url"]

        # --- Send people (one row per lead) ---
        people_sent = 0
        people_errors = 0
        seen_companies = {}  # domain -> company payload (for dedup)

        for row in rows:
            full_name = row.get("full_name") or ""
            name_parts = full_name.strip().split(" ", 1)
            domain = row.get("company_domain")
            company_linkedin_url = row.get("company_linkedin_url") or company_linkedin_map.get(domain)

            payload = {
                "client_domain": client_domain,
                "client_name": client_name,
                "lead_id": row["id"],
                "first_name": name_parts[0] if name_parts else None,
                "last_name": name_parts[1] if len(name_parts) > 1 else None,
                "full_name": full_name,
                "person_linkedin_url": row.get("person_linkedin_url"),
                "company_domain": domain,
                "company_name": row.get("company_name"),
                "company_linkedin_url": company_linkedin_url,
            }
            try:
                resp = requests.post(CLAY_PEOPLE_WEBHOOK_URL, json=payload, timeout=10)
                if resp.status_code < 400:
                    people_sent += 1
                else:
                    people_errors += 1
            except Exception:
                people_errors += 1

            # Collect unique companies for the companies webhook
            if domain and domain not in seen_companies:
                seen_companies[domain] = {
                    "client_domain": client_domain,
                    "client_name": client_name,
                    "company_name": row.get("company_name"),
                    "domain": domain,
                    "company_linkedin_url": company_linkedin_url,
                }

            time.sleep(0.1)

        # --- Send companies (deduplicated by domain) ---
        companies_sent = 0
        companies_errors = 0
        for company_payload in seen_companies.values():
            try:
                resp = requests.post(CLAY_COMPANIES_WEBHOOK_URL, json=company_payload, timeout=10)
                if resp.status_code < 400:
                    companies_sent += 1
                else:
                    companies_errors += 1
            except Exception:
                companies_errors += 1
            time.sleep(0.1)

        return {
            "success": True,
            "client_domain": client_domain,
            "total_rows": len(rows),
            "people_sent": people_sent,
            "people_errors": people_errors,
            "companies_sent": companies_sent,
            "companies_errors": companies_errors,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
