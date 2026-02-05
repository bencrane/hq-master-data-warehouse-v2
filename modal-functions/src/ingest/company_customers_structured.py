"""
Company Customers Structured Ingest Endpoint - Flat Structure

Expects flat payload:
{
  "origin_company_domain": "andela.com",
  "origin_company_name": "Andela",
  "response": "...",
  "customers": [{"url": "...", "companyName": "Resy", "hasCaseStudy": true}, ...],
  "reasoning": "...",
  "confidence": "high",
  "stepsTaken": [...]
}
"""

import os
import re
import modal
from config import app, image


def normalize_domain(raw: str) -> str:
    """Strip protocol, path, www. prefix — return bare domain."""
    d = raw.lower().strip()
    d = re.sub(r'^https?://', '', d)
    d = d.split('/')[0]
    if d.startswith('www.'):
        d = d[4:]
    return d


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_customers_structured(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = normalize_domain(request.get("origin_company_domain", ""))
        company_name = request.get("origin_company_name")

        # Flat fields
        response_text = request.get("response")
        customers = request.get("customers") or []
        reasoning = request.get("reasoning")
        confidence = request.get("confidence")
        steps_taken = request.get("stepsTaken")

        # Store raw
        raw_insert = (
            supabase.schema("raw")
            .from_("claygent_customers_structured_raw")
            .insert({
                "origin_company_domain": domain,
                "origin_company_name": company_name,
                "confidence": confidence,
                "raw_payload": {
                    "response": response_text,
                    "customers": customers,
                    "reasoning": reasoning,
                    "confidence": confidence,
                    "stepsTaken": steps_taken,
                },
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract customers
        extracted_count = 0
        core_count = 0
        staging_count = 0
        staging_errors = []
        customer_names = []

        for c in customers:
            name = c.get("companyName") if isinstance(c, dict) else None
            if not name:
                continue

            # Insert to extracted
            extracted_result = supabase.schema("extracted").from_("claygent_customers_structured").insert({
                "raw_id": raw_id,
                "origin_company_domain": domain,
                "origin_company_name": company_name,
                "customer_name": name,
                "case_study_url": c.get("url"),
                "has_case_study": c.get("hasCaseStudy"),
                "confidence": confidence,
            }).execute()

            extracted_id = extracted_result.data[0]["id"] if extracted_result.data else None

            # Upsert to core.company_customers
            supabase.schema("core").from_("company_customers").upsert({
                "origin_company_domain": domain,
                "origin_company_name": company_name,
                "customer_name": name,
                "case_study_url": c.get("url"),
                "has_case_study": c.get("hasCaseStudy"),
                "source": "claygent_structured",
                "source_id": extracted_id,
            }, on_conflict="origin_company_domain,customer_name").execute()

            # Push case study URLs to staging for Gemini extraction
            case_study_url = c.get("url")
            if case_study_url:
                try:
                    supabase.schema("raw").from_("staging_case_study_urls").upsert({
                        "origin_company_name": company_name,
                        "origin_company_domain": domain,
                        "customer_company_name": name,
                        "case_study_url": case_study_url,
                        "processed": False,
                    }, on_conflict="case_study_url").execute()
                    staging_count += 1
                except Exception as staging_err:
                    staging_errors.append(str(staging_err))

            extracted_count += 1
            core_count += 1
            customer_names.append(name)

        return {
            "success": True,
            "raw_id": str(raw_id),
            "domain": domain,
            "customers_extracted": extracted_count,
            "customers_to_core": core_count,
            "staging_case_study_urls": staging_count,
            "staging_errors": staging_errors[:3] if staging_errors else None,
            "customer_names": customer_names,
            "confidence": confidence,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("origin_company_domain", "unknown"),
        }
