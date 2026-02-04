"""
SEC Filings Fetch Endpoint

Fetches SEC filing metadata from the Submissions API and returns filtered,
actionable filing information for sales briefings.

Expects:
{
  "domain": "apple.com"
}

Returns filtered filings:
- Latest 10-Q and 10-K
- Recent 8-Ks with executive changes (5.02), earnings (2.02), material contracts (1.01)
- Document URLs for each filing
"""

import os
import modal
import httpx
from config import app, image
from typing import Optional

# SEC Submissions API
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"


def fetch_submissions(cik: str) -> dict:
    """
    Fetch filing submissions from SEC EDGAR.

    Args:
        cik: 10-digit zero-padded CIK (e.g., "0000320193")

    Returns:
        Full submissions JSON response or error dict
    """
    try:
        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        headers = {"User-Agent": "Substrate tools@substrate.build"}
        response = httpx.get(url, headers=headers, timeout=60.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"SEC API error: {e.response.status_code}", "cik": cik}
    except Exception as e:
        return {"error": str(e), "cik": cik}


def build_document_url(cik: str, accession_number: str, primary_document: str) -> str:
    """
    Build the SEC EDGAR document URL.

    Args:
        cik: CIK (will strip leading zeros for URL)
        accession_number: Filing accession number (e.g., "0000320193-25-000008")
        primary_document: Primary document filename (e.g., "aapl-20241228.htm")

    Returns:
        Full URL to the document
    """
    # Remove leading zeros from CIK for URL path
    cik_int = str(int(cik))
    # Remove dashes from accession number
    accession_no_dashes = accession_number.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_no_dashes}/{primary_document}"


def extract_relevant_filings(submissions: dict, cik: str) -> dict:
    """
    Extract sales-relevant filings from submissions response.

    Returns:
        {
            "latest_10q": { filing_date, report_date, accession_number, document_url },
            "latest_10k": { ... },
            "recent_8k_executive_changes": [ ... ],  # Item 5.02
            "recent_8k_earnings": [ ... ],           # Item 2.02
            "recent_8k_material_contracts": [ ... ]  # Item 1.01
        }
    """
    if "error" in submissions:
        return {}

    filings = submissions.get("filings", {}).get("recent", {})

    # Parallel arrays - same index = same filing
    forms = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    report_dates = filings.get("reportDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])
    items_list = filings.get("items", [])

    result = {
        "latest_10q": None,
        "latest_10k": None,
        "recent_8k_executive_changes": [],
        "recent_8k_earnings": [],
        "recent_8k_material_contracts": [],
    }

    for i, form in enumerate(forms):
        filing_date = filing_dates[i] if i < len(filing_dates) else None
        report_date = report_dates[i] if i < len(report_dates) else None
        accession = accession_numbers[i] if i < len(accession_numbers) else None
        primary_doc = primary_documents[i] if i < len(primary_documents) else None
        items = items_list[i] if i < len(items_list) else ""

        # Build document URL
        doc_url = None
        if accession and primary_doc:
            doc_url = build_document_url(cik, accession, primary_doc)

        filing_info = {
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": accession,
            "document_url": doc_url,
        }

        if form == "10-Q" and result["latest_10q"] is None:
            result["latest_10q"] = filing_info
        elif form == "10-K" and result["latest_10k"] is None:
            result["latest_10k"] = filing_info
        elif form == "8-K":
            # Check for specific 8-K item codes
            if "5.02" in items:  # Executive departures/appointments
                result["recent_8k_executive_changes"].append({
                    **filing_info,
                    "items": items,
                })
            if "2.02" in items:  # Earnings announcement
                result["recent_8k_earnings"].append({
                    **filing_info,
                    "items": items,
                })
            if "1.01" in items:  # Material contracts
                result["recent_8k_material_contracts"].append({
                    **filing_info,
                    "items": items,
                })

    # Limit 8-Ks to most recent 5 of each type
    result["recent_8k_executive_changes"] = result["recent_8k_executive_changes"][:5]
    result["recent_8k_earnings"] = result["recent_8k_earnings"][:5]
    result["recent_8k_material_contracts"] = result["recent_8k_material_contracts"][:5]

    return result


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def fetch_sec_filings(request: dict) -> dict:
    """
    Fetch SEC filings for a company domain.

    Returns filtered filings relevant for sales briefings:
    - Latest 10-Q (quarterly report)
    - Latest 10-K (annual report)
    - Recent 8-Ks with executive changes, earnings, material contracts
    """
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
        sec_company_name = payload.get("sec_company_name")

        if not cik:
            return {
                "success": False,
                "error": f"CIK is null for domain '{domain}'",
                "domain": domain,
            }

        # 2. Fetch from SEC Submissions API
        submissions = fetch_submissions(cik)

        if "error" in submissions:
            return {
                "success": False,
                "error": submissions.get("error"),
                "domain": domain,
                "cik": cik,
            }

        # 3. Extract relevant filings
        filings = extract_relevant_filings(submissions, cik)

        # Get company name from submissions if not in ticker data
        company_name = sec_company_name or submissions.get("name")

        return {
            "success": True,
            "domain": domain,
            "cik": cik,
            "ticker": ticker,
            "company_name": company_name,
            "filings": filings,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
