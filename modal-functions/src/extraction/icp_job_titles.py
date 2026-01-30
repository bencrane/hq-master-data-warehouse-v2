"""
ICP Job Titles Extraction

Extracts ICP job titles from raw payload and normalizes camelCase to human-readable format.
"""

import re
from typing import Optional

# Acronyms that should be all caps
ACRONYMS = {
    'vp': 'VP',
    'ceo': 'CEO',
    'cfo': 'CFO',
    'cto': 'CTO',
    'cio': 'CIO',
    'coo': 'COO',
    'cmo': 'CMO',
    'cro': 'CRO',
    'cso': 'CSO',
    'ciso': 'CISO',
    'cpo': 'CPO',
    'chro': 'CHRO',
    'svp': 'SVP',
    'evp': 'EVP',
    'avp': 'AVP',
    'it': 'IT',
    'hr': 'HR',
    'grc': 'GRC',
    'sdr': 'SDR',
    'bdr': 'BDR',
    'ae': 'AE',
    'am': 'AM',
    'csm': 'CSM',
    'pm': 'PM',
    'ux': 'UX',
    'ui': 'UI',
    'qa': 'QA',
    'devops': 'DevOps',
    'devsecops': 'DevSecOps',
    'saas': 'SaaS',
    'api': 'API',
    'crm': 'CRM',
    'erp': 'ERP',
}

# Words that should stay lowercase
LOWERCASE_WORDS = {'of', 'and', 'the', 'for', 'in', 'at', 'to', 'with'}


def split_camel_case(text: str) -> list[str]:
    """Split camelCase or PascalCase into words."""
    # Handle acronyms followed by capital letter (e.g., 'GRCManager' -> 'GRC', 'Manager')
    # Insert space before capitals that follow lowercase, or before a capital followed by lowercase
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    result = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', result)
    return result.split()


def normalize_job_title(camel_case_title: str) -> str:
    """
    Convert camelCase job title to human-readable format.

    Examples:
        chiefInformationSecurityOfficer -> Chief Information Security Officer
        vpOfSecurity -> VP of Security
        grcManager -> GRC Manager
        itDirector -> IT Director
    """
    words = split_camel_case(camel_case_title)
    normalized_words = []

    for i, word in enumerate(words):
        word_lower = word.lower()

        # Check if it's an acronym
        if word_lower in ACRONYMS:
            normalized_words.append(ACRONYMS[word_lower])
        # Check if it should be lowercase (but not if it's the first word)
        elif word_lower in LOWERCASE_WORDS and i > 0:
            normalized_words.append(word_lower)
        # Default: title case
        else:
            normalized_words.append(word.capitalize())

    return ' '.join(normalized_words)


def normalize_titles_list(titles: list[str]) -> list[str]:
    """Normalize a list of camelCase titles."""
    return [normalize_job_title(title) for title in titles]


def extract_icp_job_titles(
    supabase,
    raw_payload_id: str,
    company_name: str,
    domain: str,
    company_linkedin_url: Optional[str],
    raw_payload: dict,
) -> dict:
    """
    Extract and normalize ICP job titles from raw payload.
    """
    # Extract fields from payload
    reasoning = raw_payload.get("reasoning")
    raw_primary = raw_payload.get("primaryTitles", [])
    raw_influencer = raw_payload.get("influencerTitles", [])
    raw_extended = raw_payload.get("extendedTitles", [])

    source_tokens_used = raw_payload.get("tokensUsed")
    source_input_tokens = raw_payload.get("inputTokens")
    source_output_tokens = raw_payload.get("outputTokens")
    source_cost = raw_payload.get("totalCostToAIProvider")

    # Normalize titles
    primary_titles = normalize_titles_list(raw_primary)
    influencer_titles = normalize_titles_list(raw_influencer)
    extended_titles = normalize_titles_list(raw_extended)

    # Store extracted data (upsert on domain)
    extracted_record = {
        "raw_payload_id": raw_payload_id,
        "company_name": company_name,
        "domain": domain,
        "company_linkedin_url": company_linkedin_url,
        "reasoning": reasoning,
        "raw_primary_titles": raw_primary,
        "raw_influencer_titles": raw_influencer,
        "raw_extended_titles": raw_extended,
        "primary_titles": primary_titles,
        "influencer_titles": influencer_titles,
        "extended_titles": extended_titles,
        "source_tokens_used": source_tokens_used,
        "source_input_tokens": source_input_tokens,
        "source_output_tokens": source_output_tokens,
        "source_cost": source_cost,
    }

    # Upsert - update if domain exists
    extracted_result = supabase.schema("extracted").from_("icp_job_titles").upsert(
        extracted_record,
        on_conflict="domain"
    ).execute()

    return {
        "extracted_id": extracted_result.data[0]["id"],
        "primary_titles": primary_titles,
        "influencer_titles": influencer_titles,
        "extended_titles": extended_titles,
    }
