"""
Core Company Simple Ingestion Endpoint

Upserts company data directly to core.companies table.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CoreCompanySimpleRequest(BaseModel):
    name: Optional[str] = None
    domain: str
    linkedin_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_core_company_simple(request: CoreCompanySimpleRequest) -> dict:
    """
    Upsert company data to core.companies.
    If domain exists, updates name and linkedin_url.
    If domain doesn't exist, inserts new record.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        data = {
            "domain": request.domain,
            "name": request.name,
            "linkedin_url": request.linkedin_url,
        }

        result = (
            supabase.schema("core")
            .from_("companies")
            .upsert(data, on_conflict="domain")
            .execute()
        )

        record = result.data[0] if result.data else None

        return {
            "success": True,
            "id": record["id"] if record else None,
            "domain": request.domain,
            "action": "upserted",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
