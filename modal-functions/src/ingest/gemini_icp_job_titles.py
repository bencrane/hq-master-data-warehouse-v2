"""
Gemini ICP Job Titles Endpoint

Uses Gemini 3 Flash Preview to research a company and produce an exhaustive list
of job titles representing realistic buyers, champions, evaluators, and decision-makers.

Expects:
{
  "company_name": "Vanta",
  "domain": "vanta.com",
  "company_description": "..." (optional)
}

Returns:
{
  "success": true,
  "domain": "vanta.com",
  "inferred_product": "...",
  "buyer_persona": "...",
  "titles": [
    {"title": "Security Engineer", "buyerRole": "champion", "reasoning": "..."}
  ],
  "champion_titles": ["Security Engineer", ...],
  "evaluator_titles": ["CISO", ...],
  "decision_maker_titles": ["VP of Engineering", ...],
  "total_title_count": 45,
  "cost_usd": 0.00135
}
"""

import os
import json
import modal
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any

from config import app, image


class GeminiICPJobTitlesRequest(BaseModel):
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    company_description: Optional[str] = None

    @field_validator("company_name", "domain", mode="before")
    @classmethod
    def _strip_required_fields(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Field is required")
        text = str(value).strip()
        if not text:
            raise ValueError("Field cannot be empty")
        return text

    @field_validator("domain")
    @classmethod
    def _normalize_domain(cls, value: str) -> str:
        return value.lower().replace("https://", "").replace("http://", "").strip("/")

    @field_validator("company_description", mode="before")
    @classmethod
    def _normalize_company_description(cls, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


PROMPT_TEMPLATE = """CONTEXT
You are a B2B buyer persona researcher. You will be given a company name, domain, and optionally a company description. Your job is to research this company thoroughly and produce an exhaustive list of job titles that represent realistic buyers, champions, evaluators, and decision-makers for this company's product(s).

INPUTS
companyName: {company_name}
domain: {domain}
companyDescription: {company_description}

RESEARCH INSTRUCTIONS
1. Research the company
   - Visit the company website at https://{domain} to understand what they sell, who they sell to, and how they position their product.
   - Review case studies, testimonials, and customer logos to identify real buyers and users.
   - Check G2, TrustRadius, Capterra, and similar review platforms. Look specifically at reviewer job titles.
   - Review the company's LinkedIn presence and any published ICP or buyer persona content.
   - Search: "{company_name} case study" "{company_name} customer story"
   - Capture any named roles or titles.

2. Identify the buying committee
   Determine realistic roles for:
   - **Champions** — Day-to-day users or people experiencing the problem directly. They discover, evaluate, and advocate internally.
   - **Evaluators** — Technical or operational stakeholders who run POCs or compare alternatives.
   - **Decision makers** — Budget owners and signers. Only include if appropriate for this product category and price point.

3. Generate title variations
   For each persona:
   - Include realistic seniority variants (Manager, Senior Manager, Director, Head, VP, Lead) only where appropriate.
   - Include function-specific variants where relevant (e.g., Security, Compliance, GRC, IT, Engineering, Legal, Risk).

CRITICAL GUARDRAILS
- Every title must be grounded in evidence from the company website, reviews, case studies, or known buyer patterns for this category.
- Do not guess or hallucinate titles.
- Exclude roles that would reasonably not care about or buy this product.
- Do not include generic functional labels (e.g., "Information Security").
- Quantity target: 30–60 titles. More is fine if grounded. Fewer is fine if narrow. Never pad.

OUTPUT FORMAT
Return valid JSON with this exact structure:
{{
  "companyName": "{company_name}",
  "domain": "{domain}",
  "inferredProduct": "One sentence describing what the company sells and to whom, based on your research.",
  "buyerPersona": "2–3 sentences describing the buying committee — who champions it, who evaluates it, who signs off.",
  "titles": [
    {{
      "title": "Security Engineer",
      "buyerRole": "champion",
      "reasoning": "One sentence grounding this title in research evidence."
    }}
  ]
}}

The buyerRole must be one of: "champion", "evaluator", or "decision_maker"."""


def _extract_titles_by_role(titles: list, role: str) -> list[str]:
    """Extract title strings for a specific buyer role."""
    return [
        t.get("title", "").strip()
        for t in titles
        if isinstance(t, dict) and t.get("buyerRole", "").lower() == role.lower() and t.get("title")
    ]


def _extract_all_title_strings(titles: list) -> list[str]:
    """Extract all title strings."""
    return [
        t.get("title", "").strip()
        for t in titles
        if isinstance(t, dict) and t.get("title")
    ]


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=300,  # 5 minutes - web research can take time
)
@modal.fastapi_endpoint(method="POST")
def gemini_icp_job_titles(request: GeminiICPJobTitlesRequest) -> dict:
    """
    Research a company using Gemini to find ICP job titles.
    Stores raw payload and extracts titles by buyer role.
    """
    from supabase import create_client
    import google.generativeai as genai

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        domain = request.domain
        company_name = request.company_name
        company_description = request.company_description or "Not provided"

        # Build prompt
        prompt = PROMPT_TEMPLATE.format(
            company_name=company_name,
            domain=domain,
            company_description=company_description,
        )

        # Call Gemini 3 Flash Preview
        model = genai.GenerativeModel("gemini-3-flash-preview")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for consistent extraction
            ),
        )

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        # Gemini 3 Flash Preview pricing: $0.50/1M input, $3.00/1M output
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        # Parse Gemini response
        try:
            output = json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text[:2000],
                "domain": domain,
            }

        # Extract titles
        titles_raw = output.get("titles", []) if isinstance(output, dict) else []
        titles = titles_raw if isinstance(titles_raw, list) else []
        champion_titles = _extract_titles_by_role(titles, "champion")
        evaluator_titles = _extract_titles_by_role(titles, "evaluator")
        decision_maker_titles = _extract_titles_by_role(titles, "decision_maker")
        all_titles = _extract_all_title_strings(titles)

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("gemini_icp_job_titles")
            .insert({
                "company_name": company_name,
                "domain": domain,
                "company_description": company_description if company_description != "Not provided" else None,
                "raw_payload": {
                    "output": output,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                },
                "success": True,
                "cost_usd": cost_usd,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"] if raw_insert.data else None

        # Upsert to extracted table
        supabase.schema("extracted").from_("gemini_icp_job_titles").upsert(
            {
                "raw_payload_id": raw_id,
                "company_name": company_name,
                "domain": domain,
                "inferred_product": output.get("inferredProduct") if isinstance(output, dict) else None,
                "buyer_persona": output.get("buyerPersona") if isinstance(output, dict) else None,
                "champion_titles": champion_titles,
                "evaluator_titles": evaluator_titles,
                "decision_maker_titles": decision_maker_titles,
                "all_titles": all_titles,
                "total_title_count": len(titles),
                "champion_count": len(champion_titles),
                "evaluator_count": len(evaluator_titles),
                "decision_maker_count": len(decision_maker_titles),
                "cost_usd": cost_usd,
            },
            on_conflict="domain",
        ).execute()

        return {
            "success": True,
            "domain": domain,
            "company_name": company_name,
            "raw_id": str(raw_id) if raw_id else None,
            "inferred_product": output.get("inferredProduct"),
            "buyer_persona": output.get("buyerPersona"),
            "titles": titles,
            "champion_titles": champion_titles,
            "evaluator_titles": evaluator_titles,
            "decision_maker_titles": decision_maker_titles,
            "all_titles": all_titles,
            "total_title_count": len(titles),
            "champion_count": len(champion_titles),
            "evaluator_count": len(evaluator_titles),
            "decision_maker_count": len(decision_maker_titles),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
        }
