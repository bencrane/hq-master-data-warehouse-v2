"""
BuiltWith Tech Stack Ingest Endpoint

Expects:
{
  "domain": "example.com",
  "builtwith_payload": {
    "matchesFound": [...],
    "technologiesFound": "...",
    "numberOfTotalTechnologies": 360
  },
  "clay_table_url": "optional"
}
"""

import os
import json
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_builtwith(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("builtwith_payload", {})
        clay_table_url = request.get("clay_table_url")

        # Extract matchesFound array
        if isinstance(payload, dict) and "matchesFound" in payload:
            technologies = payload.get("matchesFound", [])
        elif isinstance(payload, list):
            technologies = payload
        else:
            return {"success": False, "error": "builtwith_payload must contain matchesFound array"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("builtwith_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Extract each technology
        technologies_count = 0

        for tech in technologies:
            if not isinstance(tech, dict):
                continue

            tech_name = tech.get("Name") or tech.get("name")
            if not tech_name:
                continue

            tech_url = tech.get("Link") or tech.get("link")
            tech_description = tech.get("Description") or tech.get("description")
            tech_parent = tech.get("Parent") or tech.get("parent")
            categories = tech.get("Categories") or tech.get("categories")
            first_detected = tech.get("FirstDetected") or tech.get("first_detected")
            last_detected = tech.get("LastDetected") or tech.get("last_detected")

            # Categories might be a comma-separated string, convert to list
            if isinstance(categories, str):
                categories = [c.strip() for c in categories.split(",")]

            # Insert into extracted.company_builtwith
            supabase.schema("extracted").from_("company_builtwith").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "technology_name": tech_name,
                "technology_url": tech_url,
                "technology_description": tech_description,
                "technology_parent": tech_parent,
                "categories": categories,
                "first_detected": first_detected,
                "last_detected": last_detected,
            }).execute()

            # 3. Upsert into reference.technologies
            supabase.schema("reference").from_("technologies").upsert({
                "name": tech_name,
                "url": tech_url,
                "description": tech_description,
                "parent": tech_parent,
                "categories": categories,
            }, on_conflict="name").execute()

            # 4. Map to core.company_technologies
            # Get technology_id from reference
            tech_ref = (
                supabase.schema("reference")
                .from_("technologies")
                .select("id")
                .eq("name", tech_name)
                .limit(1)
                .execute()
            )

            if tech_ref.data:
                technology_id = tech_ref.data[0]["id"]
                supabase.schema("core").from_("company_technologies").upsert({
                    "domain": domain,
                    "technology_id": technology_id,
                    "first_detected": first_detected,
                    "last_detected": last_detected,
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
