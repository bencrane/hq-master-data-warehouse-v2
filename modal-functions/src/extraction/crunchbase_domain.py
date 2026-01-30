"""
Crunchbase Domain Inference Extraction

Extracts inferred domain from Gemini response.
"""


def extract_crunchbase_domain(
    supabase,
    raw_id: str,
    company_name: str,
    crunchbase_url: str,
    gemini_response: dict,
) -> str:
    """
    Extract and store domain inference result.
    
    Returns the extracted record ID.
    """
    extracted_data = {
        "raw_payload_id": raw_id,
        "company_name": company_name,
        "crunchbase_url": crunchbase_url,
        "inferred_domain": gemini_response.get("domain"),
        "confidence": gemini_response.get("confidence"),
        "reasoning": gemini_response.get("reasoning"),
    }

    result = (
        supabase.schema("extracted")
        .from_("crunchbase_domain_inference")
        .insert(extracted_data)
        .execute()
    )

    return result.data[0]["id"] if result.data else None
