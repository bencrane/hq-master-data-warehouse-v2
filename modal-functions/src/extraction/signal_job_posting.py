"""
Clay Signal: Job Posting - Extraction

Extracts and normalizes Job Posting signal data from raw payload.
"""

from typing import Optional
from datetime import datetime
from supabase import Client


def extract_job_posting_signal(
    supabase: Client,
    raw_payload_id: str,
    domain: Optional[str],
    company_linkedin_url: Optional[str],
    job_post_data: dict,
    is_initial_check: bool = False,
    cleaned_job_title: Optional[str] = None,
    job_function: Optional[str] = None,
) -> dict:
    """
    Extracts Job Posting signal data and stores in extracted.clay_job_posting
    and core.company_job_postings.

    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        domain: Company domain
        company_linkedin_url: Company LinkedIn URL (optional)
        job_post_data: The jobPostData object from the payload
        is_initial_check: Whether this is an initial check (not a new signal)
        cleaned_job_title: Cleaned/normalized job title (from Clay enrichment)
        job_function: Job function category (from Clay enrichment)

    Returns:
        dict with extracted_id and core_id
    """
    # Parse posted_at timestamp
    posted_at = None
    posted_at_raw = job_post_data.get("posted_at") or job_post_data.get("post_on")
    if posted_at_raw:
        try:
            # Try ISO format first
            posted_at = datetime.fromisoformat(
                posted_at_raw.replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            # Try other formats
            import re
            clean_date = re.sub(r'\s+at\s+\d+:\d+.*$', '', str(posted_at_raw), flags=re.IGNORECASE)
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%B %d, %Y",
                "%b %d, %Y",
            ]
            for fmt in formats:
                try:
                    posted_at = datetime.strptime(clean_date.strip(), fmt)
                    break
                except ValueError:
                    continue

    # Build extracted record
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_linkedin_url": company_linkedin_url,
        # Company info
        "company_domain": domain,
        "company_name": job_post_data.get("company_name"),
        "company_linkedin_id": job_post_data.get("company_id"),
        # Job info
        "job_title": job_post_data.get("title"),
        "normalized_title": job_post_data.get("normalized_title"),
        "seniority": job_post_data.get("seniority"),
        "employment_type": job_post_data.get("employment_type"),
        "location": job_post_data.get("location"),
        # Job posting details
        "job_linkedin_url": job_post_data.get("url"),
        "job_linkedin_id": job_post_data.get("job_id"),
        "posted_at": posted_at.isoformat() if posted_at else None,
        # Salary info
        "salary_min": job_post_data.get("salary_min"),
        "salary_max": job_post_data.get("salary_max"),
        "salary_currency": job_post_data.get("salary_currency"),
        "salary_unit": job_post_data.get("salary_unit"),
        # Recruiter info
        "recruiter_name": job_post_data.get("recruiter_name"),
        "recruiter_linkedin_url": job_post_data.get("recruiter_url"),
        # Metadata
        "is_initial_check": is_initial_check,
    }

    result = (
        supabase.schema("extracted")
        .from_("clay_job_posting")
        .insert(extracted_data)
        .execute()
    )

    extracted_id = result.data[0]["id"] if result.data else None

    # Upsert to core.company_job_postings if we have domain and job_id
    core_id = None
    job_id = job_post_data.get("job_id")

    if domain and job_id:
        core_data = {
            "domain": domain,
            "job_id": job_id,
            "title": job_post_data.get("title"),
            "cleaned_job_title": cleaned_job_title,
            "job_function": job_function,
            "location": job_post_data.get("location"),
            "seniority": job_post_data.get("seniority"),
            "employment_type": job_post_data.get("employment_type"),
            "salary_min": job_post_data.get("salary_min"),
            "salary_max": job_post_data.get("salary_max"),
            "salary_currency": job_post_data.get("salary_currency"),
            "url": job_post_data.get("url"),
            "posted_at": posted_at.isoformat() if posted_at else None,
            "company_linkedin_url": company_linkedin_url,
        }

        core_result = (
            supabase.schema("core")
            .from_("company_job_postings")
            .upsert(core_data, on_conflict="domain,job_id")
            .execute()
        )

        core_id = core_result.data[0]["id"] if core_result.data else None

    return {
        "extracted_id": extracted_id,
        "core_id": core_id,
    }
