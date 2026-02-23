"""
Ingest Orphan Customer Domain Result

Stores the result from Gemini domain inference for orphan customers
(customers with no case study URL).

Expects:
{
  "domain": "javelintechnologies.com",
  "reason": "Aurea Software was acquired by ESW Capital...",
  "success": true,
  "cost_usd": 0.00007,
  "confidence": "high",
  "input_tokens": 412,
  "output_tokens": 71,
  "customer_company_name": "Aurea Software",
  "origin_company_domain": "12twenty.com"
}

Returns:
{
  "success": true,
  "raw_id": "uuid",
  "extracted_id": "uuid"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=30,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_orphan_customer_domain(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        customer_company_name = request.get("customer_company_name", "").strip()
        origin_company_domain = request.get("origin_company_domain", "").strip()

        if not customer_company_name:
            return {"success": False, "error": "customer_company_name is required"}
        if not origin_company_domain:
            return {"success": False, "error": "origin_company_domain is required"}

        # Store raw payload
        raw_result = (
            supabase.schema("raw")
            .from_("orphan_customer_domain_payloads")
            .insert({"payload": request})
            .execute()
        )
        raw_id = raw_result.data[0]["id"] if raw_result.data else None

        # Extract and store result
        extracted_result = (
            supabase.schema("extracted")
            .from_("orphan_customer_domain")
            .insert({
                "raw_payload_id": raw_id,
                "customer_company_name": customer_company_name,
                "origin_company_domain": origin_company_domain,
                "inferred_domain": request.get("domain"),
                "confidence": request.get("confidence"),
                "reason": request.get("reason"),
                "input_tokens": request.get("input_tokens"),
                "output_tokens": request.get("output_tokens"),
                "cost_usd": request.get("cost_usd"),
            })
            .execute()
        )
        extracted_id = extracted_result.data[0]["id"] if extracted_result.data else None

        # Update core.company_customers if domain was inferred
        inferred_domain = request.get("domain")
        if inferred_domain and request.get("success"):
            try:
                supabase.schema("core").from_("company_customers").update({
                    "customer_domain": inferred_domain,
                    "customer_domain_source": "gemini-orphan-resolve",
                }).eq(
                    "origin_company_domain", origin_company_domain
                ).eq(
                    "customer_name", customer_company_name
                ).is_(
                    "customer_domain", "null"
                ).execute()
            except Exception:
                pass  # Don't fail if core update fails

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "customer_company_name": request.get("customer_company_name", "unknown"),
        }
