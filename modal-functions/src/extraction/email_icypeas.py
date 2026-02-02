"""
Extraction logic for Icypeas email data.

Extracts email results and populates reference tables for email-to-person mapping.
"""

from typing import Optional


def extract_email_icypeas(
    supabase,
    raw_payload_id: str,
    person_linkedin_url: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
    domain: Optional[str],
    company_name: Optional[str],
    company_linkedin_url: Optional[str],
    icypeas_payload: dict,
) -> dict:
    """
    Extract Icypeas results to extracted table.
    Also updates reference tables for person mapping.

    Icypeas payload shape:
    {
        "email": "jensen@anthropic.com",
        "emails": [
            {
                "email": "jensen@anthropic.com",
                "certainty": "ultra_sure",
                "mxRecords": ["google.com"],
                "mxProvider": "google"
            }
        ],
        "status": "FOUND",
        "success": true,
        "searchId": "NLm0H5wB-su9yNYpgeim",
        "certainty": "ultra_sure"
    }

    Returns dict with extracted_id and any side effects.
    """

    # Extract from payload
    email = icypeas_payload.get("email")
    emails = icypeas_payload.get("emails", [])
    status = icypeas_payload.get("status")
    success = icypeas_payload.get("success", False)
    search_id = icypeas_payload.get("searchId")
    certainty = icypeas_payload.get("certainty")

    # Get details from first email entry if available
    mx_records = None
    mx_provider = None
    if emails and len(emails) > 0:
        first_email = emails[0]
        mx_records = first_email.get("mxRecords")
        mx_provider = first_email.get("mxProvider")
        # Use certainty from first email if not at top level
        if not certainty:
            certainty = first_email.get("certainty")

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
        "success": success,
        "search_id": search_id,
        "certainty": certainty,
        "mx_records": mx_records,
        "mx_provider": mx_provider,
        "emails": emails if emails else None,
    }

    # Insert to extracted table
    result = (
        supabase.schema("extracted")
        .from_("email_icypeas")
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
                "source": "icypeas",
            }, on_conflict="email", ignore_duplicates=True)
            .execute()
        )
        return bool(result.data)
    except Exception as e:
        # Don't fail the main extraction for reference table errors
        print(f"Warning: Failed to insert email_to_person: {e}")
        return False
