"""
Extraction logic for LeadMagic email data.

Extracts email results and updates reference.email_to_person mapping.
"""

from typing import Optional


def extract_email_leadmagic(
    supabase,
    raw_payload_id: str,
    person_linkedin_url: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
    domain: Optional[str],
    company_name: Optional[str],
    company_linkedin_url: Optional[str],
    leadmagic_payload: dict,
) -> dict:
    """
    Extract LeadMagic results to extracted table.
    Also updates reference.email_to_person mapping.

    Returns dict with extracted_id and any side effects.
    """

    # Extract from payload
    email = leadmagic_payload.get("email")
    status = leadmagic_payload.get("status")
    message = leadmagic_payload.get("message")
    has_mx = leadmagic_payload.get("has_mx")
    mx_record = leadmagic_payload.get("mx_record")
    mx_provider = leadmagic_payload.get("mx_provider")
    is_domain_catch_all = leadmagic_payload.get("is_domain_catch_all")
    employment_verified = leadmagic_payload.get("employment_verified")
    mx_security_gateway = leadmagic_payload.get("mx_security_gateway")
    credits_consumed = leadmagic_payload.get("credits_consumed")

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
        "status": status,
        "message": message,
        "has_mx": has_mx,
        "mx_record": mx_record,
        "mx_provider": mx_provider,
        "is_domain_catch_all": is_domain_catch_all,
        "employment_verified": employment_verified,
        "mx_security_gateway": mx_security_gateway,
        "credits_consumed": credits_consumed,
    }

    # Insert to extracted table
    result = (
        supabase.schema("extracted")
        .from_("email_leadmagic")
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
                "source": "leadmagic",
            }, on_conflict="email", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        # Don't fail the main extraction for reference table errors
        print(f"Warning: Failed to insert email_to_person: {e}")
        return False
