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

Fetches CIK from SEC and stores ticker + CIK in reference.sec_company_info.
"""

import os
import modal
import httpx
from config import app, image

# SEC bulk file URL - maps all tickers to CIKs
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def fetch_cik_from_sec(ticker: str) -> dict:
    """
    Fetch CIK and company name from SEC for a given ticker.
    Uses the SEC's bulk company_tickers.json file.

    Returns: {"cik": "0001234567", "company_name": "Example Inc"} or {"cik": None, "company_name": None}
    """
    try:
        response = httpx.get(SEC_TICKERS_URL, timeout=30.0)
        response.raise_for_status()
        data = response.json()

        # SEC file structure: {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc"}, ...}
        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                # CIK needs to be zero-padded to 10 digits for SEC URLs
                cik_raw = str(entry.get("cik_str", ""))
                cik_padded = cik_raw.zfill(10)
                return {
                    "cik": cik_padded,
                    "company_name": entry.get("title")
                }

        return {"cik": None, "company_name": None}
    except Exception:
        return {"cik": None, "company_name": None}


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

        # Fetch CIK from SEC
        sec_data = fetch_cik_from_sec(ticker)
        cik = sec_data.get("cik")
        sec_company_name = sec_data.get("company_name")

        # 1. Store raw payload (include fetched SEC data)
        raw_insert = (
            supabase.schema("raw")
            .from_("company_ticker_payloads")
            .insert({
                "domain": domain,
                "payload": {
                    **payload,
                    "sec_cik": cik,
                    "sec_company_name": sec_company_name,
                },
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

        # 3. Upsert into reference.sec_company_info with CIK
        supabase.schema("reference").from_("sec_company_info").upsert({
            "ticker": ticker,
            "cik": cik,
            "sec_company_name": sec_company_name,
        }, on_conflict="ticker").execute()

        return {
            "success": True,
            "domain": domain,
            "ticker": ticker,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
