"""
Ingest Gemini Domain Inference Results

Stores the results from infer_customer_domain endpoint.

Expects:
{
  "customer_company_name": "Carrefour Italy",
  "origin_company_domain": "appier.com",
  "origin_company_name": "Appier",
  "candidates": [
    {"domain": "carrefour.it", "confidence": "high", "reason": "Italian subsidiary"}
  ],
  "input_tokens": 150,
  "output_tokens": 50,
  "cost_usd": 0.00004
}

Returns:
{
  "success": true,
  "raw_payload_id": "uuid",
  "inferred_domain": "carrefour.it",
  "confidence": "high"
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
def ingest_gemini_domain_inference(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    def normalize_domain(domain: str) -> str:
        """Normalize domain: remove www, protocol, paths, etc."""
        if not domain:
            return None
        d = domain.lower().strip()
        # Remove protocol
        d = d.replace("https://", "").replace("http://", "")
        # Remove www.
        if d.startswith("www."):
            d = d[4:]
        # Remove path (everything after first /)
        if "/" in d:
            d = d.split("/")[0]
        # Remove trailing dots
        d = d.rstrip(".")
        return d if d else None

    try:
        customer_company_name = request.get("customer_company_name", "").strip()
        origin_company_domain = request.get("origin_company_domain", "").strip() or None
        origin_company_name = request.get("origin_company_name", "").strip() or None
        candidates = request.get("candidates", [])

        # Normalize domains in candidates
        for c in candidates:
            if c.get("domain"):
                c["domain"] = normalize_domain(c["domain"])

        if not customer_company_name:
            return {"success": False, "error": "customer_company_name is required"}

        # 1. Insert raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("gemini_domain_inference_payloads")
            .insert({
                "customer_company_name": customer_company_name,
                "origin_company_domain": origin_company_domain,
                "origin_company_name": origin_company_name,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Extract best candidate (first high confidence, or first candidate)
        inferred_domain = None
        confidence = None
        reason = None

        if candidates:
            # Prefer high confidence
            for c in candidates:
                if c.get("confidence") == "high":
                    inferred_domain = c.get("domain")
                    confidence = "high"
                    reason = c.get("reason")
                    break

            # Fall back to first candidate if no high confidence
            if not inferred_domain and candidates:
                inferred_domain = candidates[0].get("domain")
                confidence = candidates[0].get("confidence")
                reason = candidates[0].get("reason")

        # 3. Upsert into extracted
        supabase.schema("extracted").from_("gemini_domain_inference").upsert({
            "raw_payload_id": raw_payload_id,
            "customer_company_name": customer_company_name,
            "inferred_domain": inferred_domain,
            "confidence": confidence,
            "reason": reason,
            "source": "gemini-infer",
        }, on_conflict="customer_company_name").execute()

        return {
            "success": True,
            "raw_payload_id": str(raw_payload_id),
            "customer_company_name": customer_company_name,
            "inferred_domain": inferred_domain,
            "confidence": confidence,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "customer_company_name": request.get("customer_company_name", "unknown"),
        }
