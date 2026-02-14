"""
Company Canonical Ingestion Endpoint

Upserts canonical company data (cleaned name, linkedin_url) to core.company_canonical.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CompanyCanonicalRequest(BaseModel):
    domain: str
    original_name: Optional[str] = None
    cleaned_name: Optional[str] = None
    linkedin_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_canonical(request: CompanyCanonicalRequest) -> dict:
    """
    Upsert canonical company data.

    - domain: required, unique key
    - cleaned_name: canonical company name for outbound
    - linkedin_url: company LinkedIn URL

    Upserts on domain. Only overwrites fields if provided (non-null).
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.domain.lower().strip()

        # Build upsert data - only include non-null fields
        upsert_data = {"domain": domain}

        if request.original_name:
            upsert_data["original_name"] = request.original_name.strip()

        if request.cleaned_name:
            upsert_data["cleaned_name"] = request.cleaned_name.strip()

        if request.linkedin_url:
            # Normalize linkedin URL
            url = request.linkedin_url.strip().rstrip("/")
            url = url.replace("http://", "https://")
            if "linkedin.com" in url and not url.startswith("https://www."):
                url = url.replace("https://linkedin.com", "https://www.linkedin.com")
            upsert_data["linkedin_url"] = url

        result = (
            supabase.schema("core")
            .from_("company_canonical")
            .upsert(upsert_data, on_conflict="domain")
            .execute()
        )

        record = result.data[0] if result.data else None

        return {
            "success": True,
            "id": record["id"] if record else None,
            "domain": domain,
            "original_name": upsert_data.get("original_name"),
            "cleaned_name": upsert_data.get("cleaned_name"),
            "linkedin_url": upsert_data.get("linkedin_url"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
