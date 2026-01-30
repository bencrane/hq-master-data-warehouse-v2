"""
CB VC Portfolio Extraction

Extracts VC-company relationships from CB portfolio data.
Explodes the vc columns into individual rows.
"""

from typing import Optional, List


def extract_cb_vc_portfolio(
    supabase,
    raw_payload_id: str,
    company_name: str,
    domain: Optional[str],
    city: Optional[str],
    state: Optional[str],
    country: Optional[str],
    short_description: Optional[str],
    employee_range: Optional[str],
    last_funding_date: Optional[str],
    last_funding_type: Optional[str],
    last_funding_amount: Optional[str],
    last_equity_funding_type: Optional[str],
    last_leadership_hiring_date: Optional[str],
    founded_date: Optional[str],
    estimated_revenue_range: Optional[str],
    funding_status: Optional[str],
    total_funding_amount: Optional[str],
    total_equity_funding_amount: Optional[str],
    operating_status: Optional[str],
    company_linkedin_url: Optional[str],
    vc_names: List[Optional[str]],
) -> int:
    """
    Extract VC-company relationships.
    Creates one row per VC in the vc_names list.
    Returns count of extracted records.
    """
    extracted_count = 0

    for vc_name in vc_names:
        if not vc_name or not vc_name.strip():
            continue

        extracted_data = {
            "raw_payload_id": raw_payload_id,
            "company_name": company_name,
            "domain": domain,
            "city": city,
            "state": state,
            "country": country,
            "short_description": short_description,
            "employee_range": employee_range,
            "last_funding_date": last_funding_date,
            "last_funding_type": last_funding_type,
            "last_funding_amount": last_funding_amount,
            "last_equity_funding_type": last_equity_funding_type,
            "last_leadership_hiring_date": last_leadership_hiring_date,
            "founded_date": founded_date,
            "estimated_revenue_range": estimated_revenue_range,
            "funding_status": funding_status,
            "total_funding_amount": total_funding_amount,
            "total_equity_funding_amount": total_equity_funding_amount,
            "operating_status": operating_status,
            "company_linkedin_url": company_linkedin_url,
            "vc_name": vc_name.strip(),
        }

        supabase.schema("extracted").from_("cb_vc_portfolio").insert(
            extracted_data
        ).execute()

        extracted_count += 1

    return extracted_count
