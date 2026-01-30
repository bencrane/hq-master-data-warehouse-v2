"""
Cleaned Company Name Ingestion Endpoint

Receives cleaned company names from Clay and stores them as a canonical reference.
Used to avoid messy names like "WUNDERGROUND LLC" in favor of "Wunderground".
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CleanedCompanyNameRequest(BaseModel):
    domain: str
    original_company_name: Optional[str] = None
    cleaned_company_name: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_cleaned_company_name(request: CleanedCompanyNameRequest) -> dict:
    """
    Ingest a cleaned company name from Clay.

    1. Stores raw payload in raw.clay_cleaned_company_names
    2. Upserts to extracted.cleaned_company_names (domain is unique key)

    Payload:
        - domain: company domain (required, unique key)
        - original_company_name: the messy original name
        - cleaned_company_name: the canonical cleaned name
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # 1. Insert into raw table
        raw_data = {
            "domain": request.domain,
            "original_company_name": request.original_company_name,
            "cleaned_company_name": request.cleaned_company_name,
            "raw_payload": {
                "domain": request.domain,
                "original_company_name": request.original_company_name,
                "cleaned_company_name": request.cleaned_company_name,
            },
        }

        raw_result = (
            supabase.schema("raw")
            .from_("clay_cleaned_company_names")
            .insert(raw_data)
            .execute()
        )

        raw_id = raw_result.data[0]["id"] if raw_result.data else None

        # 2. Upsert to extracted table (domain is unique)
        extracted_data = {
            "domain": request.domain,
            "original_company_name": request.original_company_name,
            "cleaned_company_name": request.cleaned_company_name,
            "raw_payload_id": raw_id,
            "source": "clay",
        }

        extracted_result = (
            supabase.schema("extracted")
            .from_("cleaned_company_names")
            .upsert(extracted_data, on_conflict="domain")
            .execute()
        )

        extracted_record = extracted_result.data[0] if extracted_result.data else None

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_record["id"] if extracted_record else None,
            "domain": request.domain,
            "cleaned_company_name": request.cleaned_company_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
