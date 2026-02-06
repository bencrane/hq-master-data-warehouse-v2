import re
import json
from fastapi import APIRouter
from db import get_pool

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def normalize_null(value):
    """Convert 'null' string to None, trim whitespace."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if value.lower() == "null" or value == "":
            return None
    return value


def normalize_title_case(value):
    """Trim, null check, and title case."""
    value = normalize_null(value)
    if value is None:
        return None
    return value.title()


def normalize_domain(value):
    """
    Strip https://, http://, www., trailing slashes, URL paths.
    Result: clean domain only (e.g., 'stripe.com').
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Remove protocol
    value = re.sub(r'^https?://', '', value, flags=re.IGNORECASE)
    # Remove www.
    value = re.sub(r'^www\.', '', value, flags=re.IGNORECASE)
    # Remove paths, query strings, fragments (keep only domain)
    value = value.split('/')[0].split('?')[0].split('#')[0]
    # Remove trailing dots
    value = value.rstrip('.')
    # Lowercase
    value = value.lower()

    return value if value else None


def normalize_email(value):
    """Trim, lowercase, null check."""
    value = normalize_null(value)
    if value is None:
        return None
    return value.lower()


def normalize_linkedin_person_url(value):
    """
    Normalize to format: https://www.linkedin.com/in/{slug}
    Strip query params, trailing slashes, fix http:// to https://, add www.
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Extract the slug from various formats
    # Patterns: linkedin.com/in/slug, www.linkedin.com/in/slug, etc.
    match = re.search(r'linkedin\.com/in/([^/?#]+)', value, re.IGNORECASE)
    if match:
        slug = match.group(1).rstrip('/')
        return f"https://www.linkedin.com/in/{slug}"

    return value  # Return as-is if pattern doesn't match


def normalize_linkedin_company_url(value):
    """
    Normalize to format: https://www.linkedin.com/company/{slug}
    Strip query params, trailing slashes, fix http:// to https://, add www.
    """
    value = normalize_null(value)
    if value is None:
        return None

    # Extract the slug from various formats
    match = re.search(r'linkedin\.com/company/([^/?#]+)', value, re.IGNORECASE)
    if match:
        slug = match.group(1).rstrip('/')
        return f"https://www.linkedin.com/company/{slug}"

    return value  # Return as-is if pattern doesn't match


def normalize_full_name(first_name, last_name, raw_full_name):
    """
    Build full_name from normalized first/last.
    If first_name/last_name are null but full_name exists, use and split it.
    """
    # If we have both first and last, build from them
    if first_name and last_name:
        return f"{first_name} {last_name}"

    # If we have only one, use what we have
    if first_name and not last_name:
        return first_name
    if last_name and not first_name:
        return last_name

    # If no first/last but we have raw full_name, use it
    raw_full_name = normalize_null(raw_full_name)
    if raw_full_name:
        return raw_full_name.title()

    return None


def derive_first_last_from_full(full_name):
    """
    Split full_name on first space to derive first_name and last_name.
    Returns (first_name, last_name) tuple.
    """
    if not full_name:
        return None, None

    parts = full_name.strip().split(' ', 1)
    first_name = parts[0].title() if parts[0] else None
    last_name = parts[1].title() if len(parts) > 1 and parts[1] else None

    return first_name, last_name


def normalize_record(raw_record):
    """Apply all normalization rules to a raw record."""
    # Get raw_payload for fields that might only be there
    raw_payload = raw_record.get("raw_payload") or {}
    if isinstance(raw_payload, str):
        raw_payload = json.loads(raw_payload)

    # Normalize first_name and last_name
    first_name = normalize_title_case(raw_record.get("first_name"))
    last_name = normalize_title_case(raw_record.get("last_name"))
    raw_full_name = raw_record.get("full_name")

    # If first_name/last_name are null but full_name exists, derive them
    if not first_name and not last_name and raw_full_name:
        derived_first, derived_last = derive_first_last_from_full(normalize_null(raw_full_name))
        first_name = derived_first
        last_name = derived_last

    # Build full_name
    full_name = normalize_full_name(first_name, last_name, raw_full_name)

    return {
        "raw_data_id": raw_record.get("id"),
        "client_domain": raw_record.get("client_domain"),

        # Person fields
        "first_name": first_name,
        "last_name": last_name,
        "full_name": full_name,
        "person_linkedin_url": normalize_linkedin_person_url(raw_record.get("person_linkedin_url")),
        "person_city": normalize_title_case(raw_record.get("person_city")),
        "person_state": normalize_title_case(raw_record.get("person_state")),
        "person_country": normalize_title_case(raw_record.get("person_country")),
        "work_email": normalize_email(raw_record.get("work_email")),
        "phone_number": normalize_null(raw_record.get("phone_number")),

        # Company fields (company_name: trim only, no casing)
        "company_name": normalize_null(raw_record.get("company_name")),
        "domain": normalize_domain(raw_record.get("domain")),
        "company_linkedin_url": normalize_linkedin_company_url(raw_record.get("company_linkedin_url")),
        "company_city": normalize_title_case(raw_record.get("company_city")),
        "company_state": normalize_title_case(raw_record.get("company_state")),
        "company_country": normalize_title_case(raw_record.get("company_country")),

        # Additional fields from raw_payload
        "title": normalize_null(raw_payload.get("title")),
        "status": normalize_null(raw_payload.get("status")),
        "notes": normalize_null(raw_payload.get("notes")),
    }


@router.post("/normalize")
async def normalize_records(payload: dict):
    """
    Normalize a batch of raw records from hq.clients_raw_data.

    Payload: {
        "record_ids": ["uuid1", "uuid2", ...]  // IDs from hq.clients_raw_data
    }

    Or to normalize all records for a client:
    {
        "client_domain": "securitypalhq.com"
    }

    Writes normalized results to hq.clients_normalized_crm_data.
    """
    pool = get_pool()

    record_ids = payload.get("record_ids", [])
    client_domain = payload.get("client_domain", "").strip()

    if not record_ids and not client_domain:
        return {"success": False, "error": "Either record_ids or client_domain is required"}

    # Fetch raw records
    if record_ids:
        rows = await pool.fetch("""
            SELECT id, client_domain, first_name, last_name, full_name,
                   person_linkedin_url, person_city, person_state, person_country,
                   work_email, phone_number, company_name, domain,
                   company_linkedin_url, company_city, company_state, company_country,
                   raw_payload
            FROM hq.clients_raw_data
            WHERE id = ANY($1::uuid[])
        """, record_ids)
    else:
        rows = await pool.fetch("""
            SELECT id, client_domain, first_name, last_name, full_name,
                   person_linkedin_url, person_city, person_state, person_country,
                   work_email, phone_number, company_name, domain,
                   company_linkedin_url, company_city, company_state, company_country,
                   raw_payload
            FROM hq.clients_raw_data
            WHERE client_domain = $1
        """, client_domain)

    if not rows:
        return {"success": True, "records_processed": 0, "message": "No records found"}

    # Normalize and insert
    records_processed = 0
    errors = []

    for raw_record in rows:
        try:
            normalized = normalize_record(dict(raw_record))

            await pool.execute("""
                INSERT INTO hq.clients_normalized_crm_data (
                    raw_data_id, client_domain,
                    first_name, last_name, full_name,
                    person_linkedin_url, person_city, person_state, person_country,
                    work_email, phone_number,
                    company_name, domain, company_linkedin_url,
                    company_city, company_state, company_country,
                    title, status, notes
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
                )
                ON CONFLICT (raw_data_id) DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    full_name = EXCLUDED.full_name,
                    person_linkedin_url = EXCLUDED.person_linkedin_url,
                    person_city = EXCLUDED.person_city,
                    person_state = EXCLUDED.person_state,
                    person_country = EXCLUDED.person_country,
                    work_email = EXCLUDED.work_email,
                    phone_number = EXCLUDED.phone_number,
                    company_name = EXCLUDED.company_name,
                    domain = EXCLUDED.domain,
                    company_linkedin_url = EXCLUDED.company_linkedin_url,
                    company_city = EXCLUDED.company_city,
                    company_state = EXCLUDED.company_state,
                    company_country = EXCLUDED.company_country,
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    notes = EXCLUDED.notes,
                    normalized_at = NOW(),
                    updated_at = NOW()
            """,
                normalized["raw_data_id"],
                normalized["client_domain"],
                normalized["first_name"],
                normalized["last_name"],
                normalized["full_name"],
                normalized["person_linkedin_url"],
                normalized["person_city"],
                normalized["person_state"],
                normalized["person_country"],
                normalized["work_email"],
                normalized["phone_number"],
                normalized["company_name"],
                normalized["domain"],
                normalized["company_linkedin_url"],
                normalized["company_city"],
                normalized["company_state"],
                normalized["company_country"],
                normalized["title"],
                normalized["status"],
                normalized["notes"],
            )
            records_processed += 1

        except Exception as e:
            errors.append({"raw_data_id": str(raw_record["id"]), "error": str(e)})

    return {
        "success": True,
        "records_processed": records_processed,
        "errors": errors if errors else None
    }
