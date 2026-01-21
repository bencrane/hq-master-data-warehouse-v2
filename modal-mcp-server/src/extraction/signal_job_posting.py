"""
Clay Signal: Job Posting - Extraction

Extracts and normalizes Job Posting signal data from raw payload.
"""

from typing import Optional
from supabase import Client


def extract_job_posting_signal(
    supabase: Client,
    raw_payload_id: str,
    company_linkedin_url: str,
    company_name: Optional[str],
    job_title: Optional[str],
    location: Optional[str],
    company_domain: Optional[str],
    job_linkedin_url: Optional[str],
    post_on: Optional[str],
) -> dict:
    """
    Extracts Job Posting signal data and stores in extracted.clay_job_posting.
    
    Args:
        supabase: Supabase client
        raw_payload_id: ID of the raw payload record
        company_linkedin_url: Company LinkedIn URL (input)
        company_name: Company name
        job_title: Job title
        location: Job location
        company_domain: Company domain
        job_linkedin_url: LinkedIn URL for the job posting
        post_on: Date job was posted (string, will be stored as DATE)
    
    Returns:
        dict with extracted_id
    """
    # Parse post_on date if provided
    parsed_post_on = None
    if post_on:
        try:
            from datetime import datetime
            import re
            
            # Clean up the string - remove " at X:XX ..." time suffix
            clean_date = re.sub(r'\s+at\s+\d+:\d+.*$', '', post_on, flags=re.IGNORECASE)
            
            formats = [
                "%Y-%m-%d",           # 2026-01-12
                "%Y/%m/%d",           # 2026/01/12
                "%m/%d/%Y",           # 01/12/2026
                "%d/%m/%Y",           # 12/01/2026
                "%B %d, %Y",          # January 12, 2026
                "%b %d, %Y",          # Jan 12, 2026
                "%B %d %Y",           # January 12 2026
                "%b %d %Y",           # Jan 12 2026
            ]
            
            for fmt in formats:
                try:
                    parsed_post_on = datetime.strptime(clean_date.strip(), fmt).date().isoformat()
                    break
                except ValueError:
                    continue
        except Exception:
            parsed_post_on = None

    extracted_data = {
        "raw_payload_id": raw_payload_id,
        "company_linkedin_url": company_linkedin_url,
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "company_domain": company_domain,
        "job_linkedin_url": job_linkedin_url,
        "post_on": parsed_post_on,
    }

    result = (
        supabase.schema("extracted")
        .from_("clay_job_posting")
        .insert(extracted_data)
        .execute()
    )

    return {
        "extracted_id": result.data[0]["id"] if result.data else None,
    }
