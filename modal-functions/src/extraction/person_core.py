"""
Person Core Table Extraction Functions

Populates core.* tables from person profile data:
- core.people
- core.companies (for companies in experience)
- core.person_locations
- core.person_tenure
- core.person_past_employer
"""

from typing import Optional
from datetime import datetime
from urllib.parse import urlparse
import re


def normalize_domain(domain: Optional[str]) -> Optional[str]:
    """
    Normalize domain to bare format (e.g., 'example.com').
    Strips http://, https://, www., and any paths.
    """
    if not domain:
        return None

    domain = domain.strip()
    if not domain:
        return None

    # If it looks like a URL, parse it
    if domain.startswith(('http://', 'https://')):
        try:
            parsed = urlparse(domain)
            domain = parsed.netloc or parsed.path.split('/')[0]
        except Exception:
            pass
    elif '/' in domain:
        # Has a path but no scheme - take first part
        domain = domain.split('/')[0]

    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain.lower().strip() if domain else None


def upsert_core_person(supabase, linkedin_url: str, payload: dict) -> Optional[str]:
    """
    Check if person exists in core.people, insert if not.
    Returns the core.people id.
    """
    # Check if exists
    existing = (
        supabase.schema("core")
        .from_("people")
        .select("id")
        .eq("linkedin_url", linkedin_url)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # Insert new person
    result = (
        supabase.schema("core")
        .from_("people")
        .insert({
            "linkedin_url": linkedin_url,
            "linkedin_slug": payload.get("slug"),
            "full_name": payload.get("name"),
            "linkedin_url_type": "real",
        })
        .execute()
    )

    return result.data[0]["id"] if result.data else None


def upsert_core_company(supabase, domain: str, name: str = None, linkedin_url: str = None) -> Optional[str]:
    """
    Check if company exists in core.companies by domain, insert if not.
    Returns the core.companies id.
    """
    if not domain:
        return None

    domain = normalize_domain(domain)
    if not domain:
        return None

    # Check if exists
    existing = (
        supabase.schema("core")
        .from_("companies")
        .select("id")
        .eq("domain", domain)
        .execute()
    )

    if existing.data:
        return existing.data[0]["id"]

    # Insert new company
    result = (
        supabase.schema("core")
        .from_("companies")
        .insert({
            "domain": domain,
            "name": name,
            "linkedin_url": linkedin_url,
        })
        .execute()
    )

    return result.data[0]["id"] if result.data else None


def upsert_core_person_location(supabase, linkedin_url: str, payload: dict) -> Optional[str]:
    """
    Upsert person location to core.person_locations.
    Uses location_name from payload, does NOT do lookup matching here.
    """
    location_name = payload.get("location_name")
    country = payload.get("country")

    if not location_name and not country:
        return None

    # Check if exists
    existing = (
        supabase.schema("core")
        .from_("person_locations")
        .select("id")
        .eq("linkedin_url", linkedin_url)
        .execute()
    )

    data = {
        "linkedin_url": linkedin_url,
        "country": country,
        "source": "person_profile",
    }

    if existing.data:
        # Update
        result = (
            supabase.schema("core")
            .from_("person_locations")
            .update(data)
            .eq("linkedin_url", linkedin_url)
            .execute()
        )
        return existing.data[0]["id"]
    else:
        # Insert
        result = (
            supabase.schema("core")
            .from_("person_locations")
            .insert(data)
            .execute()
        )
        return result.data[0]["id"] if result.data else None


def upsert_core_person_tenure(supabase, linkedin_url: str, payload: dict) -> Optional[str]:
    """
    Calculate and upsert person tenure to core.person_tenure.
    Uses latest_start_date from the current job.
    """
    latest_exp = payload.get("latest_experience", {}) or {}
    start_date = latest_exp.get("start_date")

    if not start_date:
        return None

    # Check if exists
    existing = (
        supabase.schema("core")
        .from_("person_tenure")
        .select("id")
        .eq("linkedin_url", linkedin_url)
        .execute()
    )

    data = {
        "linkedin_url": linkedin_url,
        "job_start_date": start_date,
        "source": "person_profile",
    }

    if existing.data:
        # Update
        result = (
            supabase.schema("core")
            .from_("person_tenure")
            .update(data)
            .eq("linkedin_url", linkedin_url)
            .execute()
        )
        return existing.data[0]["id"]
    else:
        # Insert
        result = (
            supabase.schema("core")
            .from_("person_tenure")
            .insert(data)
            .execute()
        )
        return result.data[0]["id"] if result.data else None


def insert_core_person_past_employers(supabase, linkedin_url: str, payload: dict) -> int:
    """
    Insert past employers to core.person_past_employer.
    Deletes existing records for this person, then inserts new ones.
    Returns count of records inserted.
    """
    experience_array = payload.get("experience", []) or []

    if not experience_array:
        return 0

    # Filter to past employers only (is_current = false)
    past_employers = [
        exp for exp in experience_array
        if not exp.get("is_current", False)
    ]

    if not past_employers:
        return 0

    # Delete existing records for this person
    supabase.schema("core").from_("person_past_employer").delete().eq(
        "linkedin_url", linkedin_url
    ).execute()

    # Build records - dedupe by company domain
    seen_domains = set()
    records = []
    for exp in past_employers:
        domain = normalize_domain(exp.get("company_domain"))
        if domain:
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

        records.append({
            "linkedin_url": linkedin_url,
            "past_company_name": exp.get("company"),
            "past_company_domain": domain,
            "source": "person_profile",
        })

    if records:
        supabase.schema("core").from_("person_past_employer").insert(records).execute()

    return len(records)


def extract_companies_from_experience(supabase, payload: dict) -> int:
    """
    Extract unique companies from experience array and upsert to core.companies.
    Returns count of companies processed.
    """
    experience_array = payload.get("experience", []) or []

    if not experience_array:
        return 0

    # Dedupe by domain
    seen_domains = set()
    count = 0

    for exp in experience_array:
        domain = normalize_domain(exp.get("company_domain"))
        if not domain:
            continue

        if domain in seen_domains:
            continue
        seen_domains.add(domain)

        upsert_core_company(
            supabase,
            domain=domain,
            name=exp.get("company"),
            linkedin_url=exp.get("url"),
        )
        count += 1

    return count
