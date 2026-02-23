"""
Clay Customers Audit Endpoint

Receives domains that Clay processed for customer data.
Used to reconcile what Clay sent vs what's in the database.
"""

import os
import modal
from pydantic import BaseModel
from typing import List, Optional
from config import app, image


class AuditRequest(BaseModel):
    """Single domain or list of domains."""
    domain: Optional[str] = None
    domains: Optional[List[str]] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_customers_audit(request: AuditRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Handle single domain or list
        domains = []
        if request.domain:
            domains.append(request.domain.lower().strip())
        if request.domains:
            domains.extend([d.lower().strip() for d in request.domains])

        if not domains:
            return {"success": False, "error": "No domains provided"}

        # Upsert each domain
        inserted = 0
        for d in domains:
            if not d:
                continue
            supabase.schema("raw").from_("clay_customers_of_audit").upsert({
                "domain": d
            }, on_conflict="domain").execute()
            inserted += 1

        return {
            "success": True,
            "domains_recorded": inserted,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
