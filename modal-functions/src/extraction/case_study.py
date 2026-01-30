"""
Case Study Extraction Functions

Extract case study details and champions from Gemini response.
"""

from typing import Optional, List


def extract_case_study_details(
    supabase,
    raw_payload_id: str,
    case_study_url: str,
    origin_company_domain: str,
    origin_company_name: str,
    company_customer_name: str,
    gemini_response: dict
) -> Optional[str]:
    """
    Extract case study details from Gemini response to extracted.case_study_details.
    Returns the case_study_details ID.
    """
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "case_study_url": case_study_url,
        "origin_company_domain": origin_company_domain,
        "origin_company_name": origin_company_name,
        "company_customer_name": company_customer_name,
        "company_customer_domain": gemini_response.get("customer_company_domain"),
        "article_title": gemini_response.get("article_title"),
        "confidence": gemini_response.get("confidence"),
        "reasoning": gemini_response.get("reasoning"),
    }

    # Upsert on case_study_url
    result = (
        supabase.schema("extracted")
        .from_("case_study_details")
        .upsert(extracted_data, on_conflict="case_study_url")
        .execute()
    )

    return result.data[0]["id"] if result.data else None


def extract_case_study_champions(
    supabase,
    case_study_id: str,
    gemini_response: dict
) -> int:
    """
    Extract champions from Gemini response to extracted.case_study_champions.
    Deletes existing champions for this case study and inserts new ones.
    Returns count of champions extracted.
    """
    champions = gemini_response.get("champions", [])
    
    if not champions:
        return 0

    # Delete existing champions for this case study (in case of re-extraction)
    supabase.schema("extracted").from_("case_study_champions").delete().eq(
        "case_study_id", case_study_id
    ).execute()

    # Insert new champions
    extracted_count = 0
    for champion in champions:
        full_name = champion.get("full_name")
        if not full_name:
            continue

        champion_data = {
            "case_study_id": case_study_id,
            "full_name": full_name,
            "job_title": champion.get("job_title"),
            "company_name": champion.get("company_name"),
        }

        try:
            supabase.schema("extracted").from_("case_study_champions").insert(
                champion_data
            ).execute()
            extracted_count += 1
        except Exception as e:
            print(f"Failed to insert champion {full_name}: {e}")

    return extracted_count

