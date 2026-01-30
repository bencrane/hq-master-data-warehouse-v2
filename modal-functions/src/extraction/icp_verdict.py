"""
ICP Verdict Extraction

Extracts and normalizes ICP verdict data from raw payloads.
Handles two payload formats:
  - Format A: { label, rationale, ... }
  - Format B: { verdict, reason, ... }
"""


def extract_icp_verdict(supabase, raw_payload_id: str, origin_company_domain: str, company_domain: str, payload: dict):
    """
    Extract and normalize ICP verdict from raw payload.
    
    Args:
        supabase: Supabase client instance
        raw_payload_id: UUID of the raw payload record
        origin_company_domain: The company doing the evaluation
        company_domain: The company being evaluated for ICP match
        payload: The raw AI response payload
        
    Returns:
        tuple: (extracted_id, is_match)
    """
    # Normalize verdict/label to boolean
    # Handle both formats: label="yes" or verdict="Yes"
    verdict_raw = payload.get("label") or payload.get("verdict") or ""
    verdict_lower = verdict_raw.lower().strip()
    
    if verdict_lower == "yes":
        is_match = True
    elif verdict_lower == "no":
        is_match = False
    else:
        is_match = None  # Edge case: unknown verdict
    
    # Normalize reason/rationale
    match_reason = payload.get("rationale") or payload.get("reason")
    
    # Insert into extracted table
    result = (
        supabase.schema("extracted")
        .from_("icp_verdict")
        .insert({
            "raw_payload_id": raw_payload_id,
            "origin_company_domain": origin_company_domain,
            "company_domain": company_domain,
            "is_match": is_match,
            "match_reason": match_reason,
        })
        .execute()
    )
    
    extracted_id = result.data[0]["id"] if result.data else None
    
    return extracted_id, is_match
