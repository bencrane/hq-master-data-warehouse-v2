"""
ICP Industries Extraction

Extracts ICP industries from raw payload and matches to canonical industries using GPT.
"""

import json
from typing import Optional


def get_canonical_industries(supabase) -> list[str]:
    """Fetch canonical industries from reference.company_industries."""
    result = supabase.schema("reference").from_("company_industries").select("name").execute()
    return [row["name"] for row in result.data]


def match_industries_with_gpt(openai_api_key: str, raw_industries: list[str], canonical_industries: list[str]) -> dict:
    """
    Use GPT to match broad ICP industry terms to canonical industries.

    Args:
        openai_api_key: OpenAI API key
        raw_industries: List of broad terms like ["technology", "financialServices"]
        canonical_industries: List of 451 canonical industry names

    Returns:
        dict with matched_industries and token usage
    """
    from openai import OpenAI
    client = OpenAI(api_key=openai_api_key)

    # Build the prompt - include canonical list inline
    prompt = f"""You are an industry classification expert. Match each broad ICP industry term to the most relevant canonical industries.

Broad terms to match: {json.dumps(raw_industries)}

For each term, select 1-5 matching industries from this canonical list:
{json.dumps(canonical_industries)}

Return ONLY a JSON object like:
{{"technology": ["Software Development", "IT Services and IT Consulting"], "financialServices": ["Financial Services", "Banking"]}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an industry classification expert. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )

    # Parse response
    content = response.choices[0].message.content.strip()

    # Handle potential markdown code blocks
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1])

    matched_mapping = json.loads(content)

    # Flatten to unique list of all matched industries
    all_matched = set()
    for industries in matched_mapping.values():
        all_matched.update(industries)

    return {
        "matched_mapping": matched_mapping,  # Per-term mapping
        "matched_industries": list(all_matched),  # Flat unique list
        "model": "gpt-4o-mini",
        "tokens_used": response.usage.total_tokens if response.usage else None,
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
    }


def extract_and_match_icp_industries(
    supabase,
    openai_api_key: str,
    raw_payload_id: str,
    company_name: str,
    domain: str,
    company_linkedin_url: Optional[str],
    raw_payload: dict,
) -> dict:
    """
    Main extraction function.

    1. Extract industries from payload
    2. Match to canonical industries using GPT
    3. Store extracted data
    """

    # Extract fields from payload
    raw_industries = raw_payload.get("industries", [])
    reasoning = raw_payload.get("reasoning")
    source_tokens_used = raw_payload.get("tokensUsed")
    source_input_tokens = raw_payload.get("inputTokens")
    source_output_tokens = raw_payload.get("outputTokens")
    source_cost = raw_payload.get("totalCostToAIProvider")

    # Match to canonical industries using GPT
    canonical_industries = get_canonical_industries(supabase)
    match_result = match_industries_with_gpt(openai_api_key, raw_industries, canonical_industries)

    # Store extracted data (upsert on domain)
    extracted_record = {
        "raw_payload_id": raw_payload_id,
        "company_name": company_name,
        "domain": domain,
        "company_linkedin_url": company_linkedin_url,
        "reasoning": reasoning,
        "raw_industries": raw_industries,
        "matched_industries": match_result["matched_industries"],
        "source_tokens_used": source_tokens_used,
        "source_input_tokens": source_input_tokens,
        "source_output_tokens": source_output_tokens,
        "source_cost": source_cost,
        "matching_model": match_result["model"],
        "matching_tokens_used": match_result["tokens_used"],
        "matching_cost": None,  # Can calculate later if needed
    }

    # Upsert - update if domain exists
    extracted_result = supabase.schema("extracted").from_("icp_industries").upsert(
        extracted_record,
        on_conflict="domain"
    ).execute()

    return {
        "extracted_id": extracted_result.data[0]["id"],
        "raw_industries": raw_industries,
        "matched_industries": match_result["matched_industries"],
        "matched_mapping": match_result["matched_mapping"],
    }
