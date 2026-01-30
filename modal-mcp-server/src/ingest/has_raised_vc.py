"""
Has Raised VC Check

Simple endpoint that checks if a company has raised VC funding.
Looks up the company domain in extracted.vc_portfolio.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class HasRaisedVCRequest(BaseModel):
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def has_raised_vc(request: HasRaisedVCRequest) -> dict:
    """
    Check if a company has raised VC funding.
    Returns has_raised_vc boolean and VC details if found.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Normalize domain (lowercase, strip whitespace)
        domain = request.domain.lower().strip()

        # Check vc_portfolio table
        result = (
            supabase.schema("extracted")
            .from_("vc_portfolio")
            .select("vc_name, founded_date")
            .eq("domain", domain)
            .execute()
        )

        if result.data and len(result.data) > 0:
            # Get unique VC names
            vc_names = list(set([r["vc_name"] for r in result.data if r.get("vc_name")]))
            founded_date = result.data[0].get("founded_date")

            return {
                "success": True,
                "domain": domain,
                "has_raised_vc": True,
                "vc_count": len(vc_names),
                "vc_names": vc_names,
                "founded_date": founded_date,
            }
        else:
            return {
                "success": True,
                "domain": domain,
                "has_raised_vc": False,
                "vc_count": 0,
                "vc_names": [],
                "founded_date": None,
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
