"""
PredictLeads Tech Stack Ingest Endpoint

Expects:
{
  "domain": "forethought.ai",
  "predictleads_payload": {
    "total_count": 204,
    "technologies": [...],
    "technologiesFound": "..."
  },
  "clay_table_url": "optional"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_predictleads_techstack(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("predictleads_payload", {})
        clay_table_url = request.get("clay_table_url")

        # Extract technologies array
        if isinstance(payload, dict) and "technologies" in payload:
            technologies = payload.get("technologies", [])
        elif isinstance(payload, list):
            technologies = payload
        else:
            return {"success": False, "error": "predictleads_payload must contain technologies array"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("predictleads_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Process each technology
        technologies_count = 0

        for tech in technologies:
            if not isinstance(tech, dict):
                continue

            title = tech.get("title")
            if not title:
                continue

            tech_url = tech.get("url")
            tech_domain = tech.get("domain")
            categories = tech.get("categories")
            score = tech.get("score")
            first_seen_at = tech.get("first_seen_at")
            last_seen_at = tech.get("last_seen_at")
            behind_firewall = tech.get("behind_firewall")

            # Insert into extracted.company_predictleads
            supabase.schema("extracted").from_("company_predictleads").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "technology_title": title,
                "technology_url": tech_url,
                "technology_domain": tech_domain,
                "categories": categories,
                "score": score,
                "first_seen_at": first_seen_at,
                "last_seen_at": last_seen_at,
                "behind_firewall": behind_firewall,
            }).execute()

            # Upsert into reference.predictleads_technologies
            supabase.schema("reference").from_("predictleads_technologies").upsert({
                "title": title,
                "url": tech_url,
                "technology_domain": tech_domain,
                "categories": categories,
            }, on_conflict="title").execute()

            # Get reference ID and map to core
            ref = (
                supabase.schema("reference")
                .from_("predictleads_technologies")
                .select("id")
                .eq("title", title)
                .limit(1)
                .execute()
            )

            if ref.data:
                technology_id = ref.data[0]["id"]
                supabase.schema("core").from_("company_predictleads_technologies").upsert({
                    "domain": domain,
                    "technology_id": technology_id,
                    "score": score,
                    "first_seen_at": first_seen_at,
                    "last_seen_at": last_seen_at,
                    "behind_firewall": behind_firewall,
                }, on_conflict="domain,technology_id").execute()

            technologies_count += 1

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "technologies_count": technologies_count,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
