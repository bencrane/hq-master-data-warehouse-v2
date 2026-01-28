"""
Backfill Company Descriptions

Coalesces descriptions from multiple sources with priority:
1. vc_portfolio.long_description (highest)
2. company_firmographics.description
3. company_discovery.description (lowest)

See: docs/modal/workflows/backfill-company-descriptions.md
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class BackfillCompanyDescriptionsRequest(BaseModel):
    batch_size: int = 1000
    dry_run: bool = False


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
@modal.fastapi_endpoint(method="POST")
def backfill_company_descriptions(request: BackfillCompanyDescriptionsRequest) -> dict:
    """
    Backfill core.company_descriptions with priority:
    1. vc_portfolio.long_description
    2. company_firmographics.description
    3. company_discovery.description
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        source_counts = {
            "vc_portfolio": 0,
            "company_firmographics": 0,
            "company_discovery": 0,
        }
        updated_count = 0

        # 1. Get all domains with descriptions from vc_portfolio (highest priority)
        vc_result = (
            supabase.schema("extracted")
            .from_("vc_portfolio")
            .select("domain, long_description")
            .not_.is_("domain", "null")
            .not_.is_("long_description", "null")
            .limit(request.batch_size)
            .execute()
        )

        for row in vc_result.data or []:
            if not row.get("domain") or not row.get("long_description"):
                continue

            if not request.dry_run:
                supabase.schema("core").from_("company_descriptions").upsert({
                    "domain": row["domain"],
                    "description": row["long_description"],
                    "source": "vc_portfolio",
                }, on_conflict="domain").execute()

            source_counts["vc_portfolio"] += 1
            updated_count += 1

        # 2. Get domains from firmographics that aren't already covered
        firmo_result = (
            supabase.schema("extracted")
            .from_("company_firmographics")
            .select("company_domain, description")
            .not_.is_("company_domain", "null")
            .not_.is_("description", "null")
            .limit(request.batch_size)
            .execute()
        )

        # Get domains already processed
        processed_domains = {row["domain"] for row in vc_result.data or []}

        for row in firmo_result.data or []:
            domain = row.get("company_domain")
            if not domain or not row.get("description"):
                continue
            if domain in processed_domains:
                continue

            if not request.dry_run:
                supabase.schema("core").from_("company_descriptions").upsert({
                    "domain": domain,
                    "description": row["description"],
                    "source": "company_firmographics",
                }, on_conflict="domain").execute()

            processed_domains.add(domain)
            source_counts["company_firmographics"] += 1
            updated_count += 1

        # 3. Get domains from discovery that aren't already covered
        discovery_result = (
            supabase.schema("extracted")
            .from_("company_discovery")
            .select("domain, description")
            .not_.is_("domain", "null")
            .not_.is_("description", "null")
            .limit(request.batch_size)
            .execute()
        )

        for row in discovery_result.data or []:
            domain = row.get("domain")
            if not domain or not row.get("description"):
                continue
            if domain in processed_domains:
                continue

            if not request.dry_run:
                supabase.schema("core").from_("company_descriptions").upsert({
                    "domain": domain,
                    "description": row["description"],
                    "source": "company_discovery",
                }, on_conflict="domain").execute()

            processed_domains.add(domain)
            source_counts["company_discovery"] += 1
            updated_count += 1

        return {
            "success": True,
            "dry_run": request.dry_run,
            "updated_count": updated_count,
            "source_breakdown": source_counts,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
