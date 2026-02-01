"""
Job Posting Ingest Endpoint

Expects:
{
  "domain": "withcoverage.com",
  "job_posting_payload": {
    "url": "...",
    "jobPostData": {
      "title": "Claims Support Specialist",
      "normalized_title": "Support Specialist",
      "job_id": 4318795938,
      ...
    }
  },
  "clay_table_url": "optional"
}

Or flat structure:
{
  "domain": "withcoverage.com",
  "job_posting_payload": {
    "url": "...",
    "title": "...",
    "job_id": ...,
    ...
  }
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
def ingest_job_posting(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("job_posting_payload", {})
        clay_table_url = request.get("clay_table_url")

        # Handle nested jobPostData or flat structure
        if isinstance(payload, dict) and "jobPostData" in payload:
            job_data = payload.get("jobPostData", {})
        else:
            job_data = payload

        if not job_data:
            return {"success": False, "error": "No job data found in payload"}

        # Extract fields
        job_id = job_data.get("job_id")
        url = job_data.get("url") or payload.get("url")
        title = job_data.get("title")
        normalized_title = job_data.get("normalized_title") or title
        location = job_data.get("location")
        seniority = job_data.get("seniority")
        employment_type = job_data.get("employment_type")
        salary_min = job_data.get("salary_min")
        salary_max = job_data.get("salary_max")
        salary_unit = job_data.get("salary_unit")
        salary_currency = job_data.get("salary_currency")
        company_name = job_data.get("company_name")
        company_url = job_data.get("company_url")
        company_linkedin_url = job_data.get("company_url")  # LinkedIn URL
        company_id = job_data.get("company_id")
        posted_at = job_data.get("posted_at")

        # Use domain from job_data if not provided at top level
        if not domain:
            domain = (job_data.get("domain") or "").lower().strip()

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("job_posting_payloads")
            .insert({
                "domain": domain,
                "job_id": job_id,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Insert into extracted.company_job_postings
        supabase.schema("extracted").from_("company_job_postings").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "job_id": job_id,
            "url": url,
            "title": title,
            "normalized_title": normalized_title,
            "location": location,
            "seniority": seniority,
            "employment_type": employment_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_unit": salary_unit,
            "salary_currency": salary_currency,
            "company_name": company_name,
            "company_url": company_url,
            "company_linkedin_url": company_linkedin_url,
            "company_id": company_id,
            "posted_at": posted_at,
        }).execute()

        # 3. Upsert into reference.job_titles (if we have a normalized title)
        if normalized_title:
            supabase.schema("reference").from_("job_titles").upsert({
                "normalized_title": normalized_title,
            }, on_conflict="normalized_title").execute()

            # Get reference ID and map to core
            ref = (
                supabase.schema("reference")
                .from_("job_titles")
                .select("id")
                .eq("normalized_title", normalized_title)
                .limit(1)
                .execute()
            )

            if ref.data:
                job_title_id = ref.data[0]["id"]

                # 4. Upsert into core.company_job_postings
                supabase.schema("core").from_("company_job_postings").upsert({
                    "domain": domain,
                    "job_title_id": job_title_id,
                    "job_id": job_id,
                    "url": url,
                    "title": title,
                    "location": location,
                    "seniority": seniority,
                    "employment_type": employment_type,
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_currency": salary_currency,
                    "company_linkedin_url": company_linkedin_url,
                    "posted_at": posted_at,
                }, on_conflict="domain,job_id").execute()

        return {
            "success": True,
            "domain": domain,
            "job_id": job_id,
            "raw_payload_id": str(raw_payload_id),
            "title": title,
            "normalized_title": normalized_title,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
