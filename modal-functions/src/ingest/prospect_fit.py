"""
Prospect Fit Scoring

Modal endpoint that evaluates whether a prospect company would buy from a seller company.
Uses Gemini 2.5 Flash to analyze fit and return YES/NO verdict with reasoning.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CompanyInfo(BaseModel):
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None


class ProspectFitRequest(BaseModel):
    seller: CompanyInfo
    prospect: CompanyInfo


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("gemini-secret")],
)
@modal.fastapi_endpoint(method="POST")
def evaluate_prospect_fit(request: ProspectFitRequest) -> dict:
    """
    Evaluate whether a prospect company would be a good buyer for a seller company.

    Returns:
        - verdict: "YES" or "NO"
        - reason: explanation for the verdict
        - tokens_used: total tokens consumed
        - cost: estimated cost in USD
    """
    import google.generativeai as genai

    api_key = os.environ["GEMINI_API_KEY"]

    genai.configure(api_key=api_key)

    # Build context strings
    seller_context = f"**{request.seller.name}**"
    if request.seller.domain:
        seller_context += f" ({request.seller.domain})"
    if request.seller.description:
        seller_context += f"\n{request.seller.description}"

    prospect_context = f"**{request.prospect.name}**"
    if request.prospect.domain:
        prospect_context += f" ({request.prospect.domain})"
    if request.prospect.description:
        prospect_context += f"\n{request.prospect.description}"

    prompt = f"""You are a B2B sales intelligence analyst. Your task is to evaluate whether a prospect company would be a good potential customer for a seller company.

## Seller Company (the company selling)
{seller_context}

## Prospect Company (potential buyer)
{prospect_context}

## Your Task
Decide: Would this prospect company realistically buy from the seller company?

Consider:
1. Does the prospect have a need for what the seller offers?
2. Is the prospect in an industry that typically buys this type of product/service?
3. Is there any obvious mismatch (e.g., competitor, wrong industry, too small)?

You MUST give a definitive answer. No hedging.

## Response Format
Respond with ONLY valid JSON in this exact format:
{{
  "verdict": "YES" or "NO",
  "reason": "1-2 sentence explanation"
}}

Do not include any text outside the JSON object."""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        # Get token usage
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        total_tokens = input_tokens + output_tokens

        # Gemini 2.5 Flash pricing: $0.15/1M input, $0.60/1M output (as of 2025)
        cost = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

        # Parse the response
        response_text = response.text.strip()

        # Handle markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        result = json.loads(response_text)

        return {
            "success": True,
            "verdict": result.get("verdict", "UNKNOWN"),
            "reason": result.get("reason", ""),
            "seller": request.seller.name,
            "prospect": request.prospect.name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost, 6),
        }

    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse AI response: {str(e)}",
            "raw_response": response_text if 'response_text' in dir() else None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
