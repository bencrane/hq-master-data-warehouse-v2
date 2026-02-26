"""
Company Competitors Research

Stores AI-generated competitor research data into core.company_competitors_research.

Expects:
{
  "company_name": "Restaurant Associates",
  "company_description": "Hospitality and food service management company...",
  "domain": "restaurantassociates.com",
  "notes": "While Sodexo and Zerocater have...",
  "response": "The top three competitors...",
  "reasoning": "Sodexo is a global leader...",
  "confidence": "high",
  "steps_taken": ["Visited http://...", ...],
  "top_competitors": [
    {
      "competitor_name": "Sodexo",
      "competitor_domain": "sodexo.com",
      "why_it_competes": "...",
      "evidence_sources": ["https://..."]
    }
  ]
}
"""

import os
import re
import modal
from pydantic import BaseModel
from typing import Optional, List, Any

from config import app, image


def normalize_domain(domain: str) -> str:
    """Extract root domain, removing paths and protocols."""
    if not domain:
        return ""
    # Remove protocol
    domain = re.sub(r'^https?://', '', domain)
    # Remove path (keep only domain)
    domain = domain.split('/')[0]
    # Remove www
    domain = re.sub(r'^www\.', '', domain)
    return domain.lower().strip()


class CompanyCompetitorsResearchRequest(BaseModel):
    company_name: str
    domain: str
    company_description: Optional[str] = None
    notes: Optional[str] = None
    response: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[str] = None
    steps_taken: Optional[List[str]] = None
    top_competitors: Optional[List[Any]] = None


@app.function(
    image=image,
    timeout=60,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_competitors_research(request: CompanyCompetitorsResearchRequest) -> dict:
    """
    Upsert company competitors research data.

    Uses domain as unique key for upserting.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = normalize_domain(request.domain)

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not request.company_name:
            return {"success": False, "error": "No company_name provided"}

        # Build record for upsert
        record = {
            "company_name": request.company_name.strip(),
            "domain": domain,
            "updated_at": "now()",
        }

        # Add optional fields if provided
        if request.company_description:
            record["company_description"] = request.company_description.strip()
        if request.notes:
            record["notes"] = request.notes.strip()
        if request.response:
            record["response"] = request.response.strip()
        if request.reasoning:
            record["reasoning"] = request.reasoning.strip()
        if request.confidence:
            record["confidence"] = request.confidence.strip()
        if request.steps_taken:
            record["steps_taken"] = request.steps_taken
        if request.top_competitors:
            record["top_competitors"] = request.top_competitors

        # Upsert to core.company_competitors_research
        result = (
            supabase.schema("core")
            .from_("company_competitors_research")
            .upsert(record, on_conflict="domain")
            .execute()
        )

        return {
            "success": True,
            "domain": domain,
            "company_name": request.company_name,
            "id": str(result.data[0]["id"]) if result.data else None,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
        }
