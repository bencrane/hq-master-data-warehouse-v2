"""
Extraction logic for AnyMailFinder email data.

Extracts email results and infers email structure patterns.
Also populates reference tables for email-to-person mapping and domain patterns.
"""

from typing import Optional, List


def infer_email_structure(
    email: str,
    first_name: Optional[str],
    last_name: Optional[str],
) -> Optional[str]:
    """
    Infer the email structure pattern from an email and known name.

    Returns patterns like:
    - '{first}' - michael@company.com
    - '{last}' - yan@company.com
    - '{first}.{last}' - michael.yan@company.com
    - '{first}{last}' - michaelyan@company.com
    - '{f}{last}' - myan@company.com
    - '{first}{l}' - michaely@company.com
    - '{f}.{last}' - m.yan@company.com
    - '{first}_{last}' - michael_yan@company.com
    - '{last}.{first}' - yan.michael@company.com
    - '{last}{first}' - yanmichael@company.com
    - '{last}{f}' - yanm@company.com
    """
    if not email or not first_name:
        return None

    # Extract local part (before @)
    if '@' not in email:
        return None

    local_part = email.split('@')[0].lower()
    first = first_name.lower().strip()
    last = last_name.lower().strip() if last_name else ""

    if not first:
        return None

    f = first[0] if first else ""
    l = last[0] if last else ""

    # Check patterns in order of specificity
    patterns = []

    if last:
        # Full name patterns
        if local_part == f"{first}.{last}":
            return "{first}.{last}"
        if local_part == f"{first}_{last}":
            return "{first}_{last}"
        if local_part == f"{first}{last}":
            return "{first}{last}"
        if local_part == f"{last}.{first}":
            return "{last}.{first}"
        if local_part == f"{last}_{first}":
            return "{last}_{first}"
        if local_part == f"{last}{first}":
            return "{last}{first}"

        # Initial patterns
        if local_part == f"{f}{last}":
            return "{f}{last}"
        if local_part == f"{f}.{last}":
            return "{f}.{last}"
        if local_part == f"{f}_{last}":
            return "{f}_{last}"
        if local_part == f"{first}{l}":
            return "{first}{l}"
        if local_part == f"{first}.{l}":
            return "{first}.{l}"
        if local_part == f"{first}_{l}":
            return "{first}_{l}"
        if local_part == f"{last}{f}":
            return "{last}{f}"
        if local_part == f"{last}.{f}":
            return "{last}.{f}"
        if local_part == f"{f}{l}":
            return "{f}{l}"

        # Just last name
        if local_part == last:
            return "{last}"

    # Just first name
    if local_part == first:
        return "{first}"

    # Just first initial
    if local_part == f:
        return "{f}"

    # Could not determine pattern
    return None


def extract_email_anymailfinder(
    supabase,
    raw_payload_id: str,
    person_linkedin_url: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
    domain: Optional[str],
    company_name: Optional[str],
    company_linkedin_url: Optional[str],
    anymailfinder_payload: dict,
) -> dict:
    """
    Extract AnyMailFinder results to extracted table.
    Also updates reference tables for email patterns and person mapping.

    Returns dict with extracted_id and any side effects.
    """

    # Extract from payload
    results = anymailfinder_payload.get("results", {})
    input_data = anymailfinder_payload.get("input", {})

    email = results.get("email")
    validation = results.get("validation")
    alternatives = results.get("alternatives", [])
    success = anymailfinder_payload.get("success", False)
    input_not_found_error = input_data.get("not_found_error", False)

    # Build extracted record
    extracted_record = {
        "raw_payload_id": raw_payload_id,
        "person_linkedin_url": person_linkedin_url,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "domain": domain,
        "company_name": company_name,
        "company_linkedin_url": company_linkedin_url,
        "email": email,
        "validation": validation,
        "alternatives": alternatives if alternatives else None,
        "success": success,
        "input_not_found_error": input_not_found_error,
    }

    # Insert to extracted table
    result = (
        supabase.schema("extracted")
        .from_("email_anymailfinder")
        .insert(extracted_record)
        .execute()
    )

    if not result.data:
        return {"status": "error", "message": "Failed to insert extracted record"}

    extracted_id = result.data[0]["id"]

    # Side effect: update email to person reference table
    person_mapping_updated = False

    # Insert email to person mapping (if we have linkedin_url) - first record wins
    if email and person_linkedin_url:
        person_mapping_updated = _insert_email_to_person(
            supabase, email, person_linkedin_url, first_name, last_name,
            full_name, domain, company_name
        )

    return {
        "status": "success",
        "extracted_id": extracted_id,
        "person_mapping_updated": person_mapping_updated,
    }


def _insert_email_structure(
    supabase,
    domain: str,
    structure: str,
    sample_email: str,
    first_name: Optional[str],
    last_name: Optional[str],
) -> bool:
    """
    Insert email structure pattern for a domain.

    Uses INSERT with ON CONFLICT DO NOTHING.
    Allows multiple patterns per domain (unique on domain + structure).

    Returns True if inserted, False if already exists or error.
    """
    try:
        result = (
            supabase.schema("reference")
            .from_("email_structure_by_domain")
            .upsert({
                "domain": domain,
                "email_structure": structure,
                "sample_email": sample_email,
                "sample_first_name": first_name,
                "sample_last_name": last_name,
                "observation_count": 1,
                "source": "anymailfinder",
            }, on_conflict="domain,email_structure", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        # Don't fail the main extraction for reference table errors
        print(f"Warning: Failed to insert email_structure_by_domain: {e}")
        return False


def _insert_email_to_person(
    supabase,
    email: str,
    person_linkedin_url: str,
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
    domain: Optional[str],
    company_name: Optional[str],
) -> bool:
    """
    Insert email to person mapping (first record wins).

    Uses INSERT with ON CONFLICT DO NOTHING.
    Returns True if inserted, False if already exists or error.
    """
    try:
        result = (
            supabase.schema("reference")
            .from_("email_to_person")
            .upsert({
                "email": email,
                "person_linkedin_url": person_linkedin_url,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "domain": domain,
                "company_name": company_name,
                "source": "anymailfinder",
            }, on_conflict="email", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        # Don't fail the main extraction for reference table errors
        print(f"Warning: Failed to insert email_to_person: {e}")
        return False
