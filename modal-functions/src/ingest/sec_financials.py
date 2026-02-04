"""
SEC Financials Ingest Endpoint

Fetches structured financial data from SEC EDGAR XBRL CompanyFacts API.

Expects:
{
  "domain": "apple.com"
}

Looks up CIK from existing ticker data, fetches financials, stores raw + extracted.
"""

import os
import modal
import httpx
from config import app, image
from datetime import datetime

# SEC CompanyFacts API - returns structured XBRL data
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def fetch_company_facts(cik: str) -> dict:
    """
    Fetch structured financial data from SEC EDGAR.

    Args:
        cik: 10-digit zero-padded CIK (e.g., "0000320193")

    Returns:
        Full CompanyFacts JSON response or error dict
    """
    try:
        url = SEC_COMPANYFACTS_URL.format(cik=cik)
        headers = {"User-Agent": "Substrate tools@substrate.build"}
        response = httpx.get(url, headers=headers, timeout=60.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"SEC API error: {e.response.status_code}", "cik": cik}
    except Exception as e:
        return {"error": str(e), "cik": cik}


def extract_financial_metrics(facts: dict) -> list:
    """
    Extract key financial metrics from CompanyFacts response.

    Returns list of dicts with period-level financials:
    [
        {
            "period_end": "2024-12-28",
            "fiscal_year": 2025,
            "fiscal_period": "Q1",
            "form_type": "10-Q",
            "filed_date": "2025-01-30",
            "revenue": 143658000000,
            "net_income": 42084000000,
            ...
        }
    ]
    """
    if "error" in facts or "facts" not in facts:
        return []

    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    # Key metrics to extract (SEC uses various names)
    metric_mappings = {
        "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"],
        "net_income": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
        "gross_profit": ["GrossProfit"],
        "operating_income": ["OperatingIncomeLoss"],
        "total_assets": ["Assets"],
        "total_liabilities": ["Liabilities"],
        "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "eps_basic": ["EarningsPerShareBasic"],
        "eps_diluted": ["EarningsPerShareDiluted"],
        "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
    }

    # Build a dict of all periods with their metrics
    periods = {}

    for metric_name, possible_keys in metric_mappings.items():
        for key in possible_keys:
            if key in us_gaap:
                units = us_gaap[key].get("units", {})
                # Try USD first, then USD/shares for EPS
                values = units.get("USD", units.get("USD/shares", []))

                for entry in values:
                    # Only include 10-K and 10-Q filings
                    form = entry.get("form", "")
                    if form not in ("10-K", "10-Q"):
                        continue

                    period_key = f"{entry.get('fy')}_{entry.get('fp')}_{entry.get('end')}"

                    if period_key not in periods:
                        periods[period_key] = {
                            "period_end": entry.get("end"),
                            "fiscal_year": entry.get("fy"),
                            "fiscal_period": entry.get("fp"),
                            "form_type": form,
                            "filed_date": entry.get("filed"),
                            "accession_number": entry.get("accn"),
                        }

                    # Only set if not already set (first match wins)
                    if metric_name not in periods[period_key]:
                        periods[period_key][metric_name] = entry.get("val")

                break  # Found this metric, move to next

    # Convert to list and sort by period_end descending
    result = list(periods.values())
    result.sort(key=lambda x: x.get("period_end", ""), reverse=True)

    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_sec_financials(request: dict) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # 1. Look up CIK from existing ticker data
        ticker_result = (
            supabase.schema("raw")
            .from_("company_ticker_payloads")
            .select("payload")
            .eq("domain", domain)
            .not_.is_("payload->sec_cik", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not ticker_result.data:
            return {
                "success": False,
                "error": f"No CIK found for domain '{domain}'. Run ticker ingest first.",
                "domain": domain,
            }

        payload = ticker_result.data[0].get("payload", {})
        cik = payload.get("sec_cik")
        ticker = payload.get("ticker")

        if not cik:
            return {
                "success": False,
                "error": f"CIK is null for domain '{domain}'",
                "domain": domain,
            }

        # 2. Fetch from SEC CompanyFacts API
        facts = fetch_company_facts(cik)

        if "error" in facts:
            return {
                "success": False,
                "error": facts.get("error"),
                "domain": domain,
                "cik": cik,
            }

        # 3. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_sec_facts_payloads")
            .insert({
                "domain": domain,
                "cik": cik,
                "ticker": ticker,
                "payload": facts,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 4. Extract and store financial metrics
        metrics = extract_financial_metrics(facts)

        extracted_count = 0
        for metric in metrics:
            supabase.schema("extracted").from_("company_financials").upsert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "cik": cik,
                "ticker": ticker,
                "period_end": metric.get("period_end"),
                "fiscal_year": metric.get("fiscal_year"),
                "fiscal_period": metric.get("fiscal_period"),
                "form_type": metric.get("form_type"),
                "filed_date": metric.get("filed_date"),
                "accession_number": metric.get("accession_number"),
                "revenue": metric.get("revenue"),
                "net_income": metric.get("net_income"),
                "gross_profit": metric.get("gross_profit"),
                "operating_income": metric.get("operating_income"),
                "total_assets": metric.get("total_assets"),
                "total_liabilities": metric.get("total_liabilities"),
                "stockholders_equity": metric.get("stockholders_equity"),
                "eps_basic": metric.get("eps_basic"),
                "eps_diluted": metric.get("eps_diluted"),
                "operating_cash_flow": metric.get("operating_cash_flow"),
            }, on_conflict="domain,period_end,fiscal_period").execute()
            extracted_count += 1

        # Get the most recent metrics for response
        latest = metrics[0] if metrics else {}

        return {
            "success": True,
            "domain": domain,
            "cik": cik,
            "ticker": ticker,
            "sec_company_name": facts.get("entityName"),
            "raw_payload_id": raw_payload_id,
            "periods_extracted": extracted_count,
            "latest_period": {
                "period_end": latest.get("period_end"),
                "fiscal_year": latest.get("fiscal_year"),
                "fiscal_period": latest.get("fiscal_period"),
                "revenue": latest.get("revenue"),
                "net_income": latest.get("net_income"),
            } if latest else None,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
