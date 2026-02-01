"""
Company Classification (B2B/B2C) Ingest Endpoint

Expects:
{
  "domain": "example.com",
  "classification_payload": {
    "buyerClassification": {
      "businessBuyers": { "isB2b": "YES", "reason": "..." },
      "consumerBuyers": { "isB2c": "NO", "reason": "..." }
    },
    "tokensUsed": 1605,
    ...
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
def ingest_company_classification(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("classification_payload", {})
        clay_table_url = request.get("clay_table_url")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Extract classification data
        buyer_classification = payload.get("buyerClassification", {})
        business_buyers = buyer_classification.get("businessBuyers", {})
        consumer_buyers = buyer_classification.get("consumerBuyers", {})

        # Parse YES/NO to boolean
        is_b2b_str = business_buyers.get("isB2b", "").upper()
        is_b2c_str = consumer_buyers.get("isB2c", "").upper()

        is_b2b = is_b2b_str == "YES"
        is_b2c = is_b2c_str == "YES"

        b2b_reason = business_buyers.get("reason")
        b2c_reason = consumer_buyers.get("reason")

        tokens_used = payload.get("tokensUsed")

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_classification_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Insert into extracted.company_classification
        supabase.schema("extracted").from_("company_classification").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "is_b2b": is_b2b,
            "b2b_reason": b2b_reason,
            "is_b2c": is_b2c,
            "b2c_reason": b2c_reason,
            "tokens_used": tokens_used,
        }).execute()

        # 3. Upsert into core.company_business_model
        supabase.schema("core").from_("company_business_model").upsert({
            "domain": domain,
            "is_b2b": is_b2b,
            "is_b2c": is_b2c,
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "is_b2b": is_b2b,
            "is_b2c": is_b2c,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
