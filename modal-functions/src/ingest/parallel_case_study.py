"""
Ingest Parallel AI Case Study Extraction

Receives case study extraction payloads from Clay/Parallel AI and stores them.

Expects:
{
  "success": true,
  "champions": [
    {
      "champion_full_name": "Tim Custer",
      "champion_job_title": "Senior Vice President",
      "champion_testimonials_or_quotations": "Quote here..."
    }
  ],
  "case_study_url": "https://example.com/case-study",
  "customer_company_name": "Acme Corp",
  "origin_company_domain": "vendor.com",
  "customer_company_domain": "acme.com",
  "publishing_company_name": "Vendor Inc"
}

Returns:
{
  "success": true,
  "raw_payload_id": "uuid",
  "case_study_id": "uuid",
  "champions_inserted": 1
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_parallel_case_study(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Extract fields from payload
        case_study_url = request.get("case_study_url", "").strip()
        origin_company_domain = request.get("origin_company_domain", "").lower().strip()
        customer_company_name = request.get("customer_company_name", "").strip()
        customer_company_domain = request.get("customer_company_domain", "").lower().strip() or None
        publishing_company_name = request.get("publishing_company_name", "").strip() or None
        champions = request.get("champions", [])
        success = request.get("success", False)
        clay_table_url = request.get("clay_table_url")

        # Validation
        if not case_study_url:
            return {"success": False, "error": "case_study_url is required"}
        if not origin_company_domain:
            return {"success": False, "error": "origin_company_domain is required"}

        # Skip if Parallel AI extraction failed
        if not success:
            return {
                "success": False,
                "error": "Parallel AI extraction failed (success=false)",
                "case_study_url": case_study_url
            }

        # 1. Insert into raw.parallel_case_study_payloads
        raw_insert = (
            supabase.schema("raw")
            .from_("parallel_case_study_payloads")
            .insert({
                "case_study_url": case_study_url,
                "origin_company_domain": origin_company_domain,
                "clay_table_url": clay_table_url,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Upsert into extracted.parallel_case_studies
        case_study_upsert = (
            supabase.schema("extracted")
            .from_("parallel_case_studies")
            .upsert({
                "raw_payload_id": raw_payload_id,
                "case_study_url": case_study_url,
                "origin_company_domain": origin_company_domain,
                "publishing_company_name": publishing_company_name,
                "customer_company_name": customer_company_name,
                "customer_company_domain": customer_company_domain,
            }, on_conflict="case_study_url")
            .execute()
        )
        case_study_id = case_study_upsert.data[0]["id"]

        # 3. Insert champions (one row per champion)
        champions_inserted = 0
        for champion in champions:
            if not isinstance(champion, dict):
                continue

            full_name = champion.get("champion_full_name", "").strip()
            if not full_name:
                continue

            job_title = champion.get("champion_job_title", "").strip() or None
            testimonial = champion.get("champion_testimonials_or_quotations", "").strip() or None

            supabase.schema("extracted").from_("parallel_case_study_champions").insert({
                "case_study_id": case_study_id,
                "customer_company_domain": customer_company_domain,
                "origin_company_domain": origin_company_domain,
                "full_name": full_name,
                "job_title": job_title,
                "testimonial": testimonial,
            }).execute()

            champions_inserted += 1

        return {
            "success": True,
            "raw_payload_id": str(raw_payload_id),
            "case_study_id": str(case_study_id),
            "champions_inserted": champions_inserted,
            "customer_company_domain": customer_company_domain,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "case_study_url": request.get("case_study_url", "unknown"),
        }
