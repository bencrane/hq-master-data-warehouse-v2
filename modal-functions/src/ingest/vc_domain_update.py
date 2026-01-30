"""
VC Domain Update Endpoint

Update the domain field for a VC firm by name.
"""

import os
import modal
from pydantic import BaseModel

from config import app, image


class VCDomainUpdateRequest(BaseModel):
    vc_name: str
    domain: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def update_vc_domain(request: VCDomainUpdateRequest) -> dict:
    """
    Update the domain for a VC firm by matching on name.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("raw")
            .from_("vc_firms")
            .update({"domain": request.domain})
            .eq("name", request.vc_name)
            .execute()
        )

        if result.data:
            return {
                "success": True,
                "vc_name": request.vc_name,
                "domain": request.domain,
                "updated": len(result.data),
            }
        else:
            return {
                "success": False,
                "error": f"No VC firm found with name: {request.vc_name}",
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
