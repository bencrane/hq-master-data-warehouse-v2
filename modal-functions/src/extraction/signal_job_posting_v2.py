"""
Signal: Job Posting - Extraction

Extracts and normalizes job posting signal data from raw payload.
"""

from typing import Optional, Any
from datetime import datetime
from supabase import Client


def extract_signal_job_posting(
    supabase: Client,
    raw_payload_id: str,
    client_domain: str,
    job_post_data: dict,
    is_initial_check: bool = False,
    min_days_since_job_posting: int = None,
    max_days_since_job_posting: int = None,
) -> dict:
    """
    Extracts job posting signal data and stores in extracted.signal_job_posting.

    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        client_domain: Client domain for multi-tenant tracking
        job_post_data: The jobPostData object from the payload
        is_initial_check: Whether this is an initial check (not a new signal)

    Returns:
        dict with extracted_id
    """
    # Parse posted_at timestamp
    posted_at = None
    if job_post_data.get("posted_at"):
        try:
            posted_at = datetime.fromisoformat(
                job_post_data["posted_at"].replace("Z", "+00:00")
            )
        except (ValueError, AttributeError):
            posted_at = None

    # Build extracted record
    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "client_domain": client_domain,
        # Company info
        "company_domain": job_post_data.get("domain"),
        "company_name": job_post_data.get("company_name"),
        "company_linkedin_url": job_post_data.get("company_url"),
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
        # Job posting recency
        "min_days_since_job_posting": min_days_since_job_posting,
        "max_days_since_job_posting": max_days_since_job_posting,
    }

    result = (
        supabase.schema("extracted")
        .from_("signal_job_posting")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
