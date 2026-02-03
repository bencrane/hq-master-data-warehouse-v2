"""
Company Ticker Ingest Endpoint

Expects:
{
  "domain": "harness.io",
  "ticker_payload": {
    "ticker": "HARNS"
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
def ingest_company_ticker(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        payload = request.get("ticker_payload", {})
        clay_table_url = request.get("clay_table_url")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Extract ticker from payload
        ticker = payload.get("ticker", "").upper().strip()
        if not ticker:
            return {"success": False, "error": "No ticker provided in payload"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_ticker_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
                "clay_table_url": clay_table_url,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Insert into extracted.company_ticker
        supabase.schema("extracted").from_("company_ticker").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "ticker": ticker,
        }).execute()

        # 3. Upsert into reference.sec_company_info (CIK will be backfilled later)
        supabase.schema("reference").from_("sec_company_info").upsert({
            "ticker": ticker,
        }, on_conflict="ticker").execute()

        return {
            "success": True,
            "domain": domain,
            "ticker": ticker,
            "raw_payload_id": str(raw_payload_id),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
