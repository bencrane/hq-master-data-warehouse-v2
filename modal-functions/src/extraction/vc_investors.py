"""
Company VC Investors - Extraction

Extracts and normalizes VC investor data from raw payload.
Explodes vc_1 through vc_12 into individual rows.
"""

from typing import Optional
from supabase import Client


def extract_company_vc_investors(
    supabase: Client,
    raw_payload_id: str,
    company_name: str,
    company_domain: Optional[str],
    company_linkedin_url: Optional[str],
    vc_og: Optional[str],
    vc_list: list[Optional[str]],
) -> int:
    """
    Extract VC investors to individual rows.

    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_name: Company name
        company_domain: Company domain
        company_linkedin_url: Company LinkedIn URL
        vc_og: Origin VC name
        vc_list: List of VC names (vc_1 through vc_12)

    Returns:
        Count of VCs extracted
    """
    # Filter out None/empty values
    valid_vcs = [vc for vc in vc_list if vc and vc.strip()]

    if not valid_vcs:
        return 0

    # Build rows for batch insert
    rows = [
        {
            "raw_payload_id": raw_payload_id,
            "company_name": company_name,
            "company_domain": company_domain,
            "company_linkedin_url": company_linkedin_url,
            "vc_og": vc_og,
            "vc_name": vc_name.strip(),
        }
        for vc_name in valid_vcs
    ]

    # Insert all rows
    supabase.schema("extracted").from_("company_vc_investors").insert(rows).execute()

    return len(rows)
