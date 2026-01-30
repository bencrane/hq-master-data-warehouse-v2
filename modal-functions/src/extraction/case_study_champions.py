"""
Case Study Buyers Extraction

Extracts buyer (quoted person) data from case study payloads.
Explodes the people array into individual rows.
"""

from typing import Optional, List


def extract_case_study_buyers(
    supabase,
    raw_payload_id: str,
    origin_company_name: str,
    origin_company_domain: str,
    customer_company_name: Optional[str],
    customer_company_domain: Optional[str],
    case_study_url: Optional[str],
    people: List[dict],
) -> int:
    """
    Extract buyers from case study payload.
    Creates one row per person in the people array.
    Returns count of extracted records.
    """
    if not people:
        return 0

    extracted_count = 0

    for person in people:
        full_name = person.get("fullName", "").strip()
        if not full_name:
            continue

        extracted_data = {
            "raw_payload_id": raw_payload_id,
            "origin_company_name": origin_company_name,
            "origin_company_domain": origin_company_domain,
            "customer_company_name": customer_company_name or "",
            "customer_company_domain": customer_company_domain or "",
            "case_study_url": case_study_url or "",
            "buyer_full_name": full_name,
            "buyer_job_title": person.get("jobTitle", "") or "",
        }

        supabase.schema("extracted").from_("case_study_buyers").insert(
            extracted_data
        ).execute()

        extracted_count += 1

    return extracted_count
