"""
Crunchbase Domain Inference Endpoint

Uses Gemini 3 Flash to infer company domain from Crunchbase data.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.crunchbase_domain import extract_crunchbase_domain


class CrunchbaseDomainRequest(BaseModel):
    vc_name: Optional[str] = None
    vc_domain: Optional[str] = None
    workflow_slug: str = "gemini-crunchbase-domain-inference"
    company_name: str
    crunchbase_url: str
    investment_round: Optional[str] = None


INFERENCE_PROMPT = """You are inferring the primary website domain for a company based on Crunchbase data.

**Your task:**
Given a company name and its Crunchbase URL, determine the company's primary website domain.

**Rules:**
1. The Crunchbase URL slug often matches or hints at the domain (e.g., /organization/stripe → stripe.com)
2. Use the company name to verify (e.g., "Stripe" + /organization/stripe → stripe.com)
3. If investment round text mentions the company name, use it to confirm
4. Return ONLY the bare domain (e.g., "stripe.com" not "https://www.stripe.com")
5. If you cannot confidently determine the domain, return null

**Response Format:**
Return ONLY valid JSON:
{{
    "domain": "example.com" or null,
    "confidence": "high" | "medium" | "low",
    "reasoning": "Brief explanation of how you determined the domain"
}}

---

**Inputs:**

Company Name: {company_name}

Crunchbase URL: {crunchbase_url}
{investment_round_section}
{vc_section}
"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=60,
)
@modal.fastapi_endpoint(method="POST")
def infer_crunchbase_domain(request: CrunchbaseDomainRequest) -> dict:
    """
    Infer company domain from Crunchbase data using Gemini 3 Flash.
    """
    from supabase import create_client
    import google.generativeai as genai

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Build optional sections
        investment_round_section = ""
        if request.investment_round:
            investment_round_section = f"\nInvestment Round: {request.investment_round}"

        vc_section = ""
        if request.vc_name:
            vc_section = f"\nVC/Investor: {request.vc_name}"
            if request.vc_domain:
                vc_section += f" ({request.vc_domain})"

        # Build prompt
        prompt = INFERENCE_PROMPT.format(
            company_name=request.company_name,
            crunchbase_url=request.crunchbase_url,
            investment_round_section=investment_round_section,
            vc_section=vc_section,
        )

        # Call Gemini
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        # Parse response
        try:
            gemini_response = json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text,
            }

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("crunchbase_domain_inference_payloads")
            .insert({
                "company_name": request.company_name,
                "crunchbase_url": request.crunchbase_url,
                "investment_round": request.investment_round,
                "vc_name": request.vc_name,
                "vc_domain": request.vc_domain,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": gemini_response,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract result
        extracted_id = extract_crunchbase_domain(
            supabase,
            raw_id,
            request.company_name,
            request.crunchbase_url,
            gemini_response,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "inferred_domain": gemini_response.get("domain"),
            "confidence": gemini_response.get("confidence"),
            "reasoning": gemini_response.get("reasoning"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
