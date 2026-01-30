"""
Extraction logic for Clay "Promotion" signal.
Parses comma-separated array values and extracts first/primary value.
"""

from typing import Optional
from datetime import datetime


def parse_first_value(csv_string: Optional[str]) -> Optional[str]:
    """Extract first non-empty value from comma-separated string."""
    if not csv_string:
        return None
    parts = [p.strip() for p in csv_string.split(",")]
    for part in parts:
        if part:
            return part
    return None


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date from string, returns ISO format or None."""
    if not date_str:
        return None
    
    # Get first value if comma-separated
    first_date = parse_first_value(date_str)
    if not first_date:
        return None
    
    # Try ISO format first (YYYY-MM-DD)
    try:
        parsed = datetime.strptime(first_date, "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    return None


def extract_promotion_signal(
    supabase,
    raw_payload_id: str,
    person_linkedin_url: str,
    confidence: Optional[int] = None,
    previous_title: Optional[str] = None,
    new_title: Optional[str] = None,
    start_date_with_new_title: Optional[str] = None,
    lookback_threshold_days: Optional[int] = None,
) -> dict:
    """
    Extract and normalize promotion signal data.
    Handles comma-separated arrays by taking first value.
    """
    
    extracted_record = {
        "raw_payload_id": raw_payload_id,
        "person_linkedin_profile_url": person_linkedin_url,
        "confidence": str(confidence) if confidence is not None else None,
        "previous_title": parse_first_value(previous_title),
        "new_title": parse_first_value(new_title),
        "start_date_with_new_title": parse_date(start_date_with_new_title),
        "lookback_threshold_days": lookback_threshold_days,
        "started_within_threshold": True,  # Always true - records only appear if they passed threshold
    }
    
    result = (
        supabase.schema("extracted")
        .from_("clay_promotion")
        .insert(extracted_record)
        .execute()
    )
    
    if not result.data:
        return {"status": "error", "message": "Failed to insert extracted record"}
    
    return {
        "status": "success",
        "extracted_id": result.data[0]["id"]
    }
