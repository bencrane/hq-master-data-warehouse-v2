"""
CompanyEnrich Similar Companies Preview Results Ingest

Receives CompanyEnrich similar/preview results from Clay,
stores raw payload, extracts to extracted table, upserts to core.
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def ingest_companyenrich_similar_preview_results(data: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    input_domain = data.get("input_domain", "").lower().strip()
    if not input_domain:
        return {"success": False, "error": "input_domain is required"}

    items = data.get("items", [])
    scores = (data.get("metadata") or {}).get("scores", {})

    try:
        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_enrich_similar_raw")
            .insert({
                "input_domain": input_domain,
                "similarity_weight": 0.0,
                "raw_response": data,
                "status_code": 200,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_count = 0
        core_count = 0

        for item in items:
            company_id = item.get("id")
            company_domain = item.get("domain")
            score = scores.get(str(company_id)) if company_id else None

            # Extract to extracted table
            try:
                supabase.schema("extracted").from_("company_enrich_similar").insert({
                    "raw_id": raw_id,
                    "input_domain": input_domain,
                    "company_id": company_id,
                    "company_name": item.get("name"),
                    "company_domain": company_domain,
                    "company_website": item.get("website"),
                    "company_industry": item.get("industry"),
                    "company_description": item.get("description"),
                    "company_keywords": item.get("keywords"),
                    "company_logo_url": item.get("logo_url"),
                    "similarity_score": score,
                }).execute()
                extracted_count += 1
            except Exception:
                pass

            # Upsert to core table
            if company_domain:
                try:
                    supabase.schema("core").from_("company_similar_companies_preview").upsert({
                        "input_domain": input_domain,
                        "company_name": item.get("name"),
                        "company_domain": company_domain,
                        "company_industry": item.get("industry"),
                        "company_description": item.get("description"),
                        "similarity_score": score,
                        "source": "companyenrich-preview",
                    }, on_conflict="input_domain,company_domain").execute()
                    core_count += 1
                except Exception:
                    pass

        return {
            "success": True,
            "input_domain": input_domain,
            "raw_id": raw_id,
            "items_received": len(items),
            "extracted_count": extracted_count,
            "core_count": core_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
