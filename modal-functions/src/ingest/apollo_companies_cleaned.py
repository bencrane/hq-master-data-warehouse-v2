"""
Apollo Companies Cleaned - Receives cleaned company data from Clay
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class ApolloCompaniesCleanedRequest(BaseModel):
    apollo_company_url: Optional[str] = None
    company_name: Optional[str] = None
    company_headcount: Optional[str] = None
    industry: Optional[str] = None


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' or empty to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_apollo_companies_cleaned(request: ApolloCompaniesCleanedRequest) -> dict:
    """
    Ingest cleaned Apollo company data from Clay.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        data = {
            "apollo_company_url": normalize_null_string(request.apollo_company_url),
            "company_name": normalize_null_string(request.company_name),
            "company_headcount": normalize_null_string(request.company_headcount),
            "industry": normalize_null_string(request.industry),
        }

        result = (
            supabase.schema("extracted")
            .from_("apollo_companies_cleaned")
            .insert(data)
            .execute()
        )

        record_id = result.data[0]["id"] if result.data else None

        return {
            "success": True,
            "id": record_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
