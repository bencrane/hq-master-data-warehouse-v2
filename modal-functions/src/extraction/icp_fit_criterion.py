"""
ICP Fit Criterion Extraction

Extracts primary fit criterion data from raw payload.
"""

from typing import Optional


def extract_icp_fit_criterion(
    supabase,
    raw_payload_id: str,
    company_name: str,
    domain: str,
    company_linkedin_url: Optional[str],
    raw_payload: dict,
) -> dict:
    """
    Extract primary fit criterion from raw payload.
    """
    # Extract fields from payload
    reasoning = raw_payload.get("reasoning")
    primary_criterion = raw_payload.get("primaryCriterion")
    criterion_type = raw_payload.get("criterionType")
    qualifying_signals = raw_payload.get("qualifyingSignals", [])
    disqualifying_signals = raw_payload.get("disqualifyingSignals", [])
    ideal_company_attributes = raw_payload.get("idealCompanyAttributes", [])
    minimum_requirements = raw_payload.get("minimumRequirements", [])

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
        "reasoning": reasoning,
        "primary_criterion": primary_criterion,
        "criterion_type": criterion_type,
        "qualifying_signals": qualifying_signals,
        "disqualifying_signals": disqualifying_signals,
        "ideal_company_attributes": ideal_company_attributes,
        "minimum_requirements": minimum_requirements,
        "source_tokens_used": source_tokens_used,
        "source_input_tokens": source_input_tokens,
        "source_output_tokens": source_output_tokens,
        "source_cost": source_cost,
    }

    # Upsert - update if domain exists
    extracted_result = supabase.schema("extracted").from_("icp_fit_criterion").upsert(
        extracted_record,
        on_conflict="domain"
    ).execute()

    return {
        "extracted_id": extracted_result.data[0]["id"],
        "primary_criterion": primary_criterion,
        "criterion_type": criterion_type,
        "qualifying_signals": qualifying_signals,
        "disqualifying_signals": disqualifying_signals,
        "ideal_company_attributes": ideal_company_attributes,
        "minimum_requirements": minimum_requirements,
    }
