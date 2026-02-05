"""
Ingest Competitors

Stores competitor data from OpenAI discovery into raw/extracted/core tables.

Expects:
{
  "domain": "canva.com",
  "company_name": "Canva",
  "success": true,
  "competitors": [
    {"name": "Visme", "domain": "visme.co", "linkedin_url": "https://linkedin.com/company/visme"},
    ...
  ]
}
"""

import os
import re
import modal
from config import app, image


def normalize_domain(domain: str) -> str:
    """Extract root domain, removing paths and protocols."""
    if not domain:
        return ""
    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)
    # Remove path (keep only domain)
    domain = domain.split('/')[0]
    # Remove www
    domain = re.sub(r'^www\.', '', domain)
    return domain.lower().strip()


@app.function(
    image=image,
    timeout=60,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_competitors(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        origin_domain = normalize_domain(request.get("domain", ""))
        origin_company_name = request.get("company_name", "").strip()
        competitors = request.get("competitors", [])

        if not origin_domain:
            return {"success": False, "error": "No domain provided"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("competitors_payloads")
            .insert({
                "origin_domain": origin_domain,
                "origin_company_name": origin_company_name,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Process each competitor
        competitors_processed = 0
        for comp in competitors:
            if not isinstance(comp, dict):
                continue

            comp_name = comp.get("name", "").strip()
            comp_domain = normalize_domain(comp.get("domain", ""))
            comp_linkedin = comp.get("linkedin_url", "").strip()

            if not comp_domain:
                continue

            # 2a. Store in extracted (competitor relationship)
            supabase.schema("extracted").from_("company_competitors").insert({
                "raw_payload_id": raw_payload_id,
                "origin_domain": origin_domain,
                "competitor_domain": comp_domain,
                "competitor_name": comp_name,
                "competitor_linkedin_url": comp_linkedin,
            }).execute()

            # 2b. Upsert to core.companies
            supabase.schema("core").from_("companies").upsert({
                "domain": comp_domain,
                "name": comp_name,
                "linkedin_url": comp_linkedin,
                "updated_at": "now()",
            }, on_conflict="domain").execute()

            # 2c. Upsert to core.company_names
            supabase.schema("core").from_("company_names").upsert({
                "domain": comp_domain,
                "source": "openai_competitors",
                "raw_name": comp_name,
                "linkedin_url": comp_linkedin,
                "updated_at": "now()",
            }, on_conflict="domain,source").execute()

            # 2d. Upsert to core.company_social_urls (linkedin)
            if comp_linkedin:
                supabase.schema("core").from_("company_social_urls").upsert({
                    "domain": comp_domain,
                    "linkedin_url": comp_linkedin,
                    "updated_at": "now()",
                }, on_conflict="domain").execute()

            competitors_processed += 1

        return {
            "success": True,
            "origin_domain": origin_domain,
            "raw_payload_id": str(raw_payload_id),
            "competitors_processed": competitors_processed,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "origin_domain": request.get("domain", "unknown"),
        }
