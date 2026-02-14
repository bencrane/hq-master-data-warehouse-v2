"""
Attio Job Postings Sync

Upserts job postings to Attio for companies that exist in Attio.
Tracks synced records in core.attio_job_postings_sync.
"""

import os
import modal

from config import app, image


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("attio-credentials"),
    ],
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def sync_job_postings_to_attio(request: dict = None) -> dict:
    """
    Sync unsynced job postings to Attio (batch of 500).
    Tracks synced records in core.attio_job_postings_sync.
    Call repeatedly until remaining = 0.
    """
    import requests
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    attio_token = os.environ["ATTIO_ACCESS_TOKEN"]

    supabase = create_client(supabase_url, supabase_key)

    headers = {
        "Authorization": f"Bearer {attio_token}",
        "Content-Type": "application/json"
    }

    try:
        # 1. Get Attio companies and build domain -> record_id mapping
        attio_response = requests.post(
            "https://api.attio.com/v2/objects/companies/records/query",
            headers=headers,
            json={"limit": 500},
            timeout=30
        )

        if attio_response.status_code != 200:
            return {"success": False, "error": f"Failed to fetch Attio companies: {attio_response.text}"}

        attio_companies = attio_response.json().get("data", [])

        domain_to_record_id = {}
        for company in attio_companies:
            record_id = company["id"]["record_id"]
            domains = company.get("values", {}).get("domains", [])
            for d in domains:
                domain = d.get("domain")
                if domain:
                    domain_to_record_id[domain] = record_id

        attio_domains = list(domain_to_record_id.keys())

        if not attio_domains:
            return {"success": False, "error": "No Attio companies found with domains"}

        # 2. Get unsynced job postings (not in attio_job_postings_sync)
        result = supabase.rpc(
            "get_unsynced_job_postings_for_attio",
            {"domains_list": attio_domains, "batch_limit": 100}
        ).execute()

        # Fallback if RPC doesn't exist
        if not result.data:
            result = (
                supabase.schema("core")
                .from_("company_job_postings")
                .select("job_id, title, location, seniority, employment_type, salary_currency, salary_min, salary_max, url, posted_at, domain, job_function")
                .in_("domain", attio_domains)
                .not_.in_("job_id",
                    supabase.schema("core")
                    .from_("attio_job_postings_sync")
                    .select("job_id")
                )
                .limit(100)
                .execute()
            )

        job_postings = result.data or []

        if not job_postings:
            return {
                "success": True,
                "message": "All job postings already synced",
                "remaining": 0,
                "synced_this_batch": 0,
            }

        # 3. Upsert to Attio and track
        success_count = 0
        error_count = 0
        errors = []

        for jp in job_postings:
            values = {
                "job_id_5": jp["job_id"],
                "title": jp["title"],
                "location": jp["location"] or "Unknown",
            }

            if jp.get("seniority"):
                values["seniority"] = jp["seniority"]
            if jp.get("employment_type"):
                values["employment_type"] = jp["employment_type"]
            if jp.get("salary_currency"):
                values["salary_currency"] = jp["salary_currency"]
            if jp.get("salary_min"):
                values["salary_min_5"] = float(jp["salary_min"])
            if jp.get("salary_max"):
                values["salary_max_1"] = float(jp["salary_max"])
            if jp.get("url"):
                values["job_posting_url"] = jp["url"]
            if jp.get("posted_at"):
                posted_at = jp["posted_at"]
                if hasattr(posted_at, 'strftime'):
                    values["posted_at"] = posted_at.strftime("%Y-%m-%d")
                elif posted_at:
                    values["posted_at"] = str(posted_at)[:10]
            if jp.get("domain"):
                values["domain"] = jp["domain"]
            if jp.get("job_function"):
                values["job_function"] = jp["job_function"]

            company_record_id = domain_to_record_id.get(jp.get("domain"))
            if company_record_id:
                values["company_8"] = company_record_id

            try:
                response = requests.put(
                    "https://api.attio.com/v2/objects/job_postings/records",
                    headers=headers,
                    params={"matching_attribute": "job_id_5"},
                    json={"data": {"values": values}},
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    success_count += 1
                    attio_record_id = response.json().get("data", {}).get("id", {}).get("record_id")

                    # Track in sync table
                    supabase.schema("core").from_("attio_job_postings_sync").upsert({
                        "job_id": jp["job_id"],
                        "attio_record_id": attio_record_id,
                    }, on_conflict="job_id").execute()
                else:
                    error_count += 1
                    if len(errors) < 5:
                        errors.append({
                            "job_id": jp["job_id"],
                            "status": response.status_code,
                            "error": response.text[:200]
                        })
            except Exception as e:
                error_count += 1
                if len(errors) < 5:
                    errors.append({"job_id": jp["job_id"], "error": str(e)})

        # 4. Count remaining
        remaining_result = (
            supabase.schema("core")
            .from_("company_job_postings")
            .select("job_id", count="exact")
            .in_("domain", attio_domains)
            .execute()
        )
        total_for_attio = remaining_result.count or 0

        synced_result = (
            supabase.schema("core")
            .from_("attio_job_postings_sync")
            .select("job_id", count="exact")
            .execute()
        )
        total_synced = synced_result.count or 0

        return {
            "success": True,
            "synced_this_batch": success_count,
            "errors_this_batch": error_count,
            "total_synced": total_synced,
            "total_for_attio": total_for_attio,
            "remaining": total_for_attio - total_synced,
            "sample_errors": errors,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
