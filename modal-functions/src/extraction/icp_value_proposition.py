"""
ICP Value Proposition Extraction

Extracts core value proposition data from raw payload.
"""

from typing import Optional


def extract_icp_value_proposition(
    supabase,
    raw_payload_id: str,
    company_name: str,
    domain: str,
    company_linkedin_url: Optional[str],
    raw_payload: dict,
) -> dict:
    """
    Extract core value proposition from raw payload.
    """
    # Extract fields from payload (matching Clay's actual keys)
    confidence = raw_payload.get("confidence")
    value_proposition = raw_payload.get("valueProp")
    core_benefit = raw_payload.get("coreBenefit")
    target_customer = raw_payload.get("targetCustomer")
    key_differentiator = raw_payload.get("keyDifferentiator")

    source_tokens_used = raw_payload.get("tokensUsed")
    source_input_tokens = raw_payload.get("inputTokens")
    source_output_tokens = raw_payload.get("outputTokens")
    source_cost = raw_payload.get("totalCostToAIProvider")

    # Store extracted data (upsert on domain)
    extracted_record = {
        "raw_payload_id": raw_payload_id,
        "company_name": company_name,
        "domain": domain,
        "company_linkedin_url": company_linkedin_url,
        "confidence": confidence,
        "value_proposition": value_proposition,
        "core_benefit": core_benefit,
        "target_customer": target_customer,
        "key_differentiator": key_differentiator,
        "source_tokens_used": source_tokens_used,
        "source_input_tokens": source_input_tokens,
        "source_output_tokens": source_output_tokens,
        "source_cost": source_cost,
    }

    # Upsert - update if domain exists
    extracted_result = supabase.schema("extracted").from_("icp_value_proposition").upsert(
        extracted_record,
        on_conflict="domain"
    ).execute()

    return {
        "extracted_id": extracted_result.data[0]["id"],
        "value_proposition": value_proposition,
        "core_benefit": core_benefit,
        "target_customer": target_customer,
        "key_differentiator": key_differentiator,
        "confidence": confidence,
    }
