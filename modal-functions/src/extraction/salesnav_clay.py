"""
SalesNav Clay Extraction Functions

Extract and flatten Clay webhook payload for SalesNav person and company data.
Maps Clay field names to database columns.
"""

from typing import Optional
from urllib.parse import urlparse
from datetime import date


def extract_domain_from_url(url: Optional[str]) -> Optional[str]:
    """Extract domain from a URL, handling various formats."""
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.lower() if domain else None
    except Exception:
        return None


def normalize_null_string(value) -> Optional[str]:
    """Convert string 'null' or empty to actual None."""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() in ("", "null", "NULL", "None"):
            return None
        return value.strip()
    return str(value)


def parse_boolean_string(value) -> Optional[bool]:
    """Parse boolean from string."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().lower() in ("", "null", "none"):
            return None
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def parse_job_start_date(value: Optional[str]) -> Optional[date]:
    """
    Parse job start date from MM-YYYY format to date.
    Returns first of the month.
    """
    if not value:
        return None
    value = value.strip()
    if not value or value.lower() in ("null", "none"):
        return None

    try:
        # Expected format: MM-YYYY (e.g., "05-2025")
        parts = value.split("-")
        if len(parts) == 2:
            month = int(parts[0])
            year = int(parts[1])
            if 1 <= month <= 12 and 1900 <= year <= 2100:
                return date(year, month, 1)
    except (ValueError, IndexError):
        pass

    return None


def parse_headcount(value) -> Optional[int]:
    """Parse headcount from string or int."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if not value or value.lower() in ("null", "none"):
            return None
        try:
            return int(value)
        except ValueError:
            return None
    return None


def extract_salesnav_clay_person(
    supabase,
    raw_payload_id: str,
    payload: dict,
) -> dict:
    """
    Extract SalesNav person data from Clay payload to extracted.salesnav_scrapes_person.

    Maps Clay field names (e.g., "First name") to database columns (e.g., "first_name").

    Returns the inserted record.
    """
    # Extract domain from Company website
    company_website = normalize_null_string(payload.get("Company website"))
    domain = extract_domain_from_url(company_website)

    # Get LinkedIn URL - try both field names
    linkedin_url = normalize_null_string(
        payload.get("LinkedIn URL (user profile)") or
        payload.get("person_linkedin_sales_nav_url")
    )

    # Build extracted record with Clay field mapping
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "first_name": normalize_null_string(payload.get("First name")),
        "last_name": normalize_null_string(payload.get("Last name")),
        "email": normalize_null_string(payload.get("Email")),
        "phone_number": normalize_null_string(payload.get("Phone number")),
        "location_raw": normalize_null_string(payload.get("Location")),
        "job_title": normalize_null_string(payload.get("Job title")),
        "profile_headline": normalize_null_string(payload.get("Profile headline")),
        "profile_summary": normalize_null_string(payload.get("Profile summary")),
        "job_description": normalize_null_string(payload.get("Job description")),
        "job_started_on": normalize_null_string(payload.get("Job started on")),
        "company_name": normalize_null_string(payload.get("Company")),
        "domain": domain,
        "company_linkedin_url": normalize_null_string(payload.get("LinkedIn URL (company)")),
        "person_linkedin_sales_nav_url": linkedin_url,
        "linkedin_user_profile_urn": normalize_null_string(payload.get("LinkedIn user profile URN")),
        "export_title": normalize_null_string(payload.get("_export_title")),
        "export_timestamp": normalize_null_string(payload.get("_export_timestamp")),
        "notes": normalize_null_string(payload.get("_notes")),
        "matching_filters": parse_boolean_string(payload.get("Matching filters")),
    }

    # Also add linkedin_url column if it exists (some schemas use this)
    if linkedin_url:
        extracted_data["linkedin_url"] = linkedin_url

    result = (
        supabase.schema("extracted")
        .from_("salesnav_scrapes_person")
        .insert(extracted_data)
        .execute()
    )

    return result.data[0] if result.data else None


def extract_salesnav_clay_company(
    supabase,
    payload: dict,
) -> dict:
    """
    Extract SalesNav company data from Clay payload to extracted.salesnav_scrapes_companies.

    Maps Clay field names to database columns.
    Note: raw_payload_id is not used because the FK constraint references a different raw table.

    Returns the inserted record.
    """
    # Extract domain from Company website
    company_website = normalize_null_string(payload.get("Company website"))
    domain = extract_domain_from_url(company_website)

    # Build extracted record with Clay field mapping
    # Note: raw_payload_id omitted due to FK constraint to different raw table
    extracted_data = {
        "company_name": normalize_null_string(payload.get("Company")),
        "linkedin_url": normalize_null_string(payload.get("LinkedIn URL (company)")),
        "linkedin_urn": normalize_null_string(payload.get("Linkedin company profile URN")),
        "domain": domain,
        "description": normalize_null_string(payload.get("Company description")),
        "headcount": parse_headcount(payload.get("Company headcount")),
        "industries": normalize_null_string(payload.get("Company industries")),
        "registered_address_raw": normalize_null_string(payload.get("Company registered address")),
    }

    result = (
        supabase.schema("extracted")
        .from_("salesnav_scrapes_companies")
        .insert(extracted_data)
        .execute()
    )

    return result.data[0] if result.data else None
