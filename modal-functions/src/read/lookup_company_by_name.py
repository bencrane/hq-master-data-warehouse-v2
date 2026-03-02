"""
Lookup Company by Name

Returns domain and linkedin_url for a given company name.
Only returns a match if there's exactly 1 close/exact match.
"""

import os
import re
import modal
from config import app, image


# Common suffixes to strip for matching
COMPANY_SUFFIXES = [
    r",?\s+Inc\.?$",
    r",?\s+LLC\.?$",
    r",?\s+Ltd\.?$",
    r",?\s+Corp\.?$",
    r",?\s+Corporation$",
    r",?\s+Co\.?$",
    r",?\s+Company$",
    r",?\s+Limited$",
    r",?\s+PLC$",
    r",?\s+GmbH$",
    r",?\s+AG$",
    r",?\s+S\.?A\.?$",
    r",?\s+B\.?V\.?$",
    r",?\s+N\.?V\.?$",
]


def normalize_company_name(name: str) -> str:
    """Strip common suffixes and normalize for matching."""
    normalized = name.strip()
    for suffix in COMPANY_SUFFIXES:
        normalized = re.sub(suffix, "", normalized, flags=re.IGNORECASE)
    return normalized.strip()


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_company_by_name(request: dict) -> dict:
    """
    Lookup company by name - returns domain and linkedin_url.

    Only returns a match if exactly 1 close/exact match is found.

    Input: {"company_name": "Hyundai Motor Company"}
    Output: {
        "success": true,
        "found": true,
        "company_name": "Hyundai Motor Company",
        "matched_name": "Hyundai Motor Company",
        "domain": "hyundai.com",
        "linkedin_url": "https://www.linkedin.com/company/hyundai"
    }
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    company_name = request.get("company_name", "").strip()

    if not company_name:
        return {"success": False, "error": "company_name is required"}

    try:
        # Strategy 1: Exact match on cleaned_name (case-insensitive)
        result = (
            supabase.schema("core")
            .from_("company_canonical")
            .select("domain, original_name, cleaned_name, linkedin_url")
            .ilike("cleaned_name", company_name)
            .execute()
        )

        if len(result.data) == 1:
            record = result.data[0]
            return {
                "success": True,
                "found": True,
                "match_type": "exact_cleaned_name",
                "company_name": company_name,
                "matched_name": record.get("cleaned_name"),
                "domain": record.get("domain"),
                "linkedin_url": record.get("linkedin_url"),
            }

        # Strategy 2: Exact match on original_name (case-insensitive)
        if len(result.data) != 1:
            result = (
                supabase.schema("core")
                .from_("company_canonical")
                .select("domain, original_name, cleaned_name, linkedin_url")
                .ilike("original_name", company_name)
                .execute()
            )

            if len(result.data) == 1:
                record = result.data[0]
                return {
                    "success": True,
                    "found": True,
                    "match_type": "exact_original_name",
                    "company_name": company_name,
                    "matched_name": record.get("cleaned_name") or record.get("original_name"),
                    "domain": record.get("domain"),
                    "linkedin_url": record.get("linkedin_url"),
                }

        # Strategy 3: Try normalized name (strip suffixes)
        normalized = normalize_company_name(company_name)
        if normalized != company_name:
            result = (
                supabase.schema("core")
                .from_("company_canonical")
                .select("domain, original_name, cleaned_name, linkedin_url")
                .ilike("cleaned_name", normalized)
                .execute()
            )

            if len(result.data) == 1:
                record = result.data[0]
                return {
                    "success": True,
                    "found": True,
                    "match_type": "normalized_cleaned_name",
                    "company_name": company_name,
                    "normalized_to": normalized,
                    "matched_name": record.get("cleaned_name"),
                    "domain": record.get("domain"),
                    "linkedin_url": record.get("linkedin_url"),
                }

        # No unique match found
        match_count = len(result.data) if result.data else 0
        return {
            "success": True,
            "found": False,
            "company_name": company_name,
            "reason": "no_unique_match",
            "matches_found": match_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e), "company_name": company_name}
